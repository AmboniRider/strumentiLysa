# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Prima adozione dell'updater intranet su una postazione già installata.

Eseguire con il Python della postazione, passando la cartella del programma.
Il bootstrap non importa il codice vecchio e usa lo stesso staging e rollback
della nuova release, dopo aver verificato lo ZIP della condivisione.
"""

from __future__ import annotations

import argparse
import ast
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from zipfile import ZipFile

SHARE = Path(r"\\srvshare\lab_dati\SOFTWARE_DATI\Strumenti")
LIMIT = 100 * 1024 * 1024


def init_terminal(title: str) -> None:
    """Identifica questa manutenzione anche fra più console aperte."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    print(f"\033]0;{title}\007\033[93m\n╔{'═' * (len(title) + 6)}╗\n"
          f"║   \033[96m{title}\033[93m   ║\n╚{'═' * (len(title) + 6)}╝\033[0m\n")


def bounded_read(path: Path, limit: int) -> bytes:
    """Limita i dati ricevuti prima di verificarli o aprire l'archivio."""
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        raise ValueError("File condiviso troppo grande")
    return content


def prepare_bootstrap(root: Path, share: Path, destination: Path) -> None:
    """Verifica ZIP e singoli digest prima di rendere importabili i nuovi moduli."""
    manifest = json.loads(bounded_read(share / "update-manifest.json", 1024 * 1024))
    version = manifest["version"]
    import re
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Versione non valida")
    tree = ast.parse((root / "src/__init__.py").read_text(encoding="utf-8"))
    current = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets))
    if tuple(map(int, current.split("."))) >= tuple(map(int, version.split("."))):
        raise ValueError(f"Versione {current} già aggiornata o successiva a {version}")
    payload = bounded_read(share / f"strumenti-update-{version}.zip", LIMIT)
    if hashlib.sha256(payload).hexdigest() != manifest["package"]["sha256"]:
        raise ValueError("Checksum ZIP programma errato")
    with ZipFile(io.BytesIO(payload)) as archive:
        files = manifest["files"]
        if len(archive.namelist()) != len(files) or set(archive.namelist()) != set(files):
            raise ValueError("File ZIP inattesi")
        if sum(info.file_size for info in archive.infolist()) > LIMIT:
            raise ValueError("Archivio decompresso troppo grande")
        for name, digest in files.items():
            path = PurePosixPath(name)
            if (path.is_absolute() or str(path) != name or "\\" in name or ":" in name or
                    any(part.startswith(".") for part in path.parts)):
                raise ValueError("Percorso ZIP non valido")
            content = archive.read(name)
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f"File alterato: {name}")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)


def main() -> None:
    """Prepara con codice verificato e affida l'installazione al runner esterno."""
    init_terminal("STRUMENTI LYSA - AGGIORNAMENTO INTRANET")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("installation", type=Path, help="Cartella locale del programma già installato")
    args = parser.parse_args()
    root = args.installation.resolve()
    if (root / ".git").exists() or not (root / ".tools/uv.exe").is_file():
        raise ValueError("Serve una postazione installata da pacchetto, senza .git e con uv locale")
    (root / ".updates").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bootstrap-", dir=root / ".updates") as temporary:
        prepare_bootstrap(root, SHARE, Path(temporary))
        # Nessun modulo applicativo è stato importato: la precedenza è solo
        # per il runtime appena verificato, mai per il vecchio codice installato.
        sys.path.insert(0, temporary)
        from src.intranet_updates import check_intranet_release
        from src.update_service import stage_release
        release = check_intranet_release("0.0.0", SHARE)
        if release.manifest["database"]["mode"] == "reset":
            raise ValueError("Il bootstrap iniziale non consente il reset dei dati")
        with closing(sqlite3.connect((root / "data/strumenti.db").as_uri() + "?mode=ro", uri=True)) as conn:
            schema = conn.execute("PRAGMA user_version").fetchone()[0]
        job = stage_release(release, root, schema)
        # Le vecchie postazioni hanno un runner che non conosce le wheel offline.
        shutil.copyfile(job / "payload/update_runner.py", job / "runner.py")
    print(f"Pacchetto {release.version} e dipendenze verificati. {release.database_message}")
    print("Chiudere il programma. Saranno creati backup e copie per il ripristino in:", job)
    if input("Installare e riavviare? Digitare SI per confermare: ").strip().upper() != "SI":
        print("Installazione annullata. Nessun file del programma modificato.")
        return
    subprocess.Popen([getattr(sys, "_base_executable", sys.executable), str(job / "runner.py"),
                      str(root), str(job)], cwd=root,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    print("Installazione avviata. Attendere il riavvio del programma.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Aggiornamento non avviato: {exc}", file=sys.stderr)
        sys.exit(1)
