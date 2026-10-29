# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Pubblica nuove versioni intranet dopo il sync Git, senza distribuire dati."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from zipfile import ZipFile

from build_release import build_intranet_release
from src import __version__
from src.intranet_updates import INTRANET_DIRECTORY, package_name, validate_offline
from src.update_service import validate_manifest, version_tuple
from trasfer import PROJECT_ROOT, init_terminal


def publish_new_version(root: Path, directory: Path) -> bool:
    """Pubblica solo versioni successive; restituisce False se già aggiornato.

    Un lock di directory SMB serializza i publisher. Gli archivi versionati
    restano immutabili; solo dopo copia e verifica il manifest diventa visibile.
    La directory condivisa deve già esistere, per non creare destinazioni errate.
    """
    if not directory.is_dir():
        raise RuntimeError(f"Cartella intranet non accessibile: {directory}")
    lock = directory / ".publish.lock"
    try:
        lock.mkdir()
    except FileExistsError as exc:
        raise RuntimeError("Pubblicazione intranet già in corso (.publish.lock). Se interrotta, verificare il lock prima di rimuoverlo.") from exc
    created_archives: list[Path] = []
    committed = False
    try:
        current = directory / "update-manifest.json"
        if current.exists():
            manifest = json.loads(current.read_text(encoding="utf-8"))
            validate_manifest(manifest, manifest["version"])
            validate_offline(manifest)
            if version_tuple(manifest["version"]) >= version_tuple(__version__):
                print(f"Intranet già aggiornata: {manifest['version']} (locale {__version__}).")
                return False
        # Staging sempre nuovo: non riutilizzare una build precedente dello
        # stesso numero di versione, che potrebbe contenere codice diverso.
        (root / "dist").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="sync-intranet-", dir=root / "dist") as temporary:
            source = Path(temporary) / "release"
            target = build_intranet_release(root, source)
            manifest = json.loads(target.read_text(encoding="utf-8"))
            validate_manifest(manifest, __version__)
            offline = validate_offline(manifest)
            archives = [(package_name(__version__), manifest["package"]["sha256"], manifest["files"]),
                        (offline["package"], offline["sha256"], offline["files"])]
            for name, digest, files in archives:
                path = source / name
                if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                    raise RuntimeError(f"Checksum archivio errato: {name}")
                with ZipFile(path) as archive:
                    if len(archive.namelist()) != len(files) or set(archive.namelist()) != set(files):
                        raise RuntimeError(f"File inattesi: {name}")
                    for filename, expected in files.items():
                        if hashlib.sha256(archive.read(filename)).hexdigest() != expected:
                            raise RuntimeError(f"File alterato: {filename}")
            names = [entry[0] for entry in archives] + ["aggiorna_intranet.py", "LEGGIMI-AGGIORNAMENTO.txt",
                                                       "SHA256SUMS.txt", "update-manifest.json"]
            # Preflight prima di qualunque copia: non sostituire mai archivi
            # già presenti con contenuto differente sotto lo stesso nome.
            for name, _, _ in archives:
                existing = directory / name
                if existing.exists() and existing.read_bytes() != (source / name).read_bytes():
                    raise RuntimeError(f"Archivio già presente con contenuto diverso: {name}. Incrementare la versione.")
            for name in names:
                content = (source / name).read_bytes()
                expected = hashlib.sha256(content).digest()
                # Temporanei e rinomina sulla stessa share: il manifest resta
                # quello precedente se una copia si interrompe o fallisce.
                descriptor, temporary_name = tempfile.mkstemp(prefix=".upload-", dir=directory)
                upload = Path(temporary_name)
                try:
                    with os.fdopen(descriptor, "wb") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    if hashlib.sha256(upload.read_bytes()).digest() != expected:
                        raise RuntimeError(f"Verifica copia intranet fallita: {name}")
                    if name.endswith(".zip") and not (directory / name).exists():
                        created_archives.append(directory / name)
                    os.replace(upload, directory / name)
                    if name == "update-manifest.json":
                        committed = True
                finally:
                    upload.unlink(missing_ok=True)
            print(f"Intranet aggiornata e verificata: {__version__} in {directory}")
            return True
    finally:
        try:
            # Rimuove solo archivi nuovi di questo tentativo non pubblicato:
            # una successiva build può così ritentare senza collisioni di timestamp.
            if not committed:
                for archive in created_archives:
                    archive.unlink(missing_ok=True)
        finally:
            lock.rmdir()


def main() -> int:
    """CLI di manutenzione usata dal quinto passo di sync.bat."""
    init_terminal("STRUMENTI LYSA - SYNC INTRANET")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=INTRANET_DIRECTORY)
    args = parser.parse_args()
    try:
        publish_new_version(PROJECT_ROOT, args.directory)
    except Exception as exc:
        print(f"Pubblicazione intranet non completata: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
