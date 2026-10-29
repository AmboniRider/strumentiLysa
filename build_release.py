# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Genera un pacchetto aggiornamento senza database e il relativo manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib
from urllib.parse import urlparse
from zipfile import ZIP_DEFLATED, ZipFile

from src import __version__
from src.update_service import REPOSITORY, SCHEMA_VERSION, UpdateError, download, safe_runtime_path, validate_manifest
from src.intranet_updates import validate_offline
from trasfer import RUNTIME_FILES, init_terminal, launcher_batch


def build_release(root: Path, output: Path, mode: str = "migrate", losses: str = "",
                  minimum_schema: int = 0, maximum_schema: int = SCHEMA_VERSION) -> Path:
    """Crea ZIP e manifest con soli file gestiti e digest di ogni contenuto."""
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    if version != __version__:
        raise ValueError("Versioni del pacchetto e del codice non allineate")
    contents = {name: (root / name).read_bytes() for name in RUNTIME_FILES}
    # Il launcher installato è diverso da quello di sviluppo: includiamo quello
    # generato, con bootstrap di recupero prima dell'accesso alla .venv.
    contents["strumenti.bat"] = launcher_batch().replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    files = {name: hashlib.sha256(content).hexdigest() for name, content in contents.items()}
    if not all(safe_runtime_path(name) for name in files):
        raise ValueError("Whitelist trasferimento contiene file non aggiornabili")
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"strumenti-update-{version}.zip"
    with ZipFile(archive, "x", ZIP_DEFLATED) as package:
        for name in sorted(files):
            package.writestr(name, contents[name])
    manifest = {
        "format": 1, "version": version,
        "python": {"min": [3, 11], "max_exclusive": [3, 14]},
        "database": {"mode": mode, "min_schema": minimum_schema, "max_schema": maximum_schema,
                     "target_schema": SCHEMA_VERSION, "losses": losses},
        "package": {"url": f"https://github.com/{REPOSITORY}/releases/download/v{version}/{archive.name}",
                    "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()},
        "files": files,
    }
    validate_manifest(manifest, version)
    target = output / "update-manifest.json"
    with target.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
    return target


def main() -> None:
    """CLI riproducibile; la pubblicazione su GitHub è un passo separato."""
    init_terminal("STRUMENTI LYSA - PACCHETTO RELEASE")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("dist/release"))
    parser.add_argument("--mode", choices=("preserve", "migrate", "reset"), default="migrate")
    parser.add_argument("--losses", default="")
    parser.add_argument("--min-schema", type=int, default=0)
    parser.add_argument("--max-schema", type=int, default=SCHEMA_VERSION)
    parser.add_argument("--intranet-offline", action="store_true",
                        help="Include le wheel Windows x64 Python 3.11–3.13 e i checksum per SMB")
    args = parser.parse_args()
    builder = build_intranet_release if args.intranet_offline else build_release
    print(builder(Path(__file__).resolve().parent, args.output, args.mode, args.losses,
                  args.min_schema, args.max_schema))


def runtime_wheels(root: Path) -> list[dict]:
    """Seleziona dal lock solo la chiusura runtime e wheel Windows supportate.

    Non si copiano ambienti virtuali o cache della macchina di sviluppo. I tre
    ABI CPython coprono l'intero intervallo ammesso dal manifest corrente.
    """
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    packages = {entry["name"]: entry for entry in lock["package"]}
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["name"]
    pending = [item["name"] for item in packages[project].get("dependencies", [])]
    visited: set[str] = set()
    wheels: list[dict] = []
    while pending:
        name = pending.pop()
        if name in visited:
            continue
        visited.add(name)
        package = packages[name]
        pending.extend(item["name"] for item in package.get("dependencies", []))
        selected = []
        for wheel in package.get("wheels", []):
            filename = Path(urlparse(wheel["url"]).path).name
            if (filename.endswith("-none-any.whl") or
                    re.search(r"-cp31[123]-(?:cp31[123]|abi3)-win_amd64\.whl$", filename)):
                if urlparse(wheel["url"]).hostname != "files.pythonhosted.org":
                    raise ValueError("Origine wheel non autorizzata nel lock")
                selected.append(wheel)
        if not selected:
            raise ValueError(f"Wheel Windows offline mancante per {name}")
        wheels.extend(selected)
    return wheels


def build_intranet_release(root: Path, output: Path, mode: str = "migrate", losses: str = "",
                           minimum_schema: int = 0, maximum_schema: int = SCHEMA_VERSION) -> Path:
    """Prepara in staging una distribuzione offline; pubblicazione SMB separata.

    Il PC che prepara la release usa Internet per le wheel bloccate. I client
    ricevono solo archivi verificabili e non devono contattare alcun servizio.
    """
    if output.exists():
        raise FileExistsError(f"Usare una cartella nuova: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".intranet-", dir=output.parent))
    try:
        uv = shutil.which("uv")
        if uv is None:
            raise RuntimeError("uv necessario per esportare il lock runtime")
        result = subprocess.run([uv, "--no-cache", "export", "--locked", "--offline", "--no-dev", "--no-emit-project",
                                 "--no-header", "--no-annotate"], cwd=root, capture_output=True)
        if result.returncode:
            raise RuntimeError("Esportazione uv.lock fallita: " + result.stderr.decode("utf-8", errors="replace"))
        contents = {"requirements.txt": result.stdout}
        for wheel in runtime_wheels(root):
            try:
                content = download(wheel["url"])
            except UpdateError as exc:
                raise RuntimeError("Download delle dipendenze PyPI non riuscito: verificare rete e certificati") from exc
            if "sha256:" + hashlib.sha256(content).hexdigest() != wheel["hash"]:
                raise ValueError("Checksum wheel diverso da uv.lock")
            contents[Path(urlparse(wheel["url"]).path).name] = content
        manifest_path = build_release(root, staging, mode, losses, minimum_schema, maximum_schema)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        archive = staging / f"strumenti-dependencies-{manifest['version']}.zip"
        with ZipFile(archive, "x", ZIP_DEFLATED) as package:
            for name, content in sorted(contents.items()):
                package.writestr(name, content)
        manifest["offline"] = {
            "package": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "files": {name: hashlib.sha256(content).hexdigest() for name, content in contents.items()},
        }
        manifest["notes"] = (root / "RELEASE_NOTES.md").read_text(encoding="utf-8")
        validate_offline(manifest)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        shutil.copyfile(root / "aggiorna_intranet.py", staging / "aggiorna_intranet.py")
        # L'istruzione accompagna i tre file necessari e spiega la prima adozione.
        (staging / "LEGGIMI-AGGIORNAMENTO.txt").write_text(
            f"STRUMENTI LYSA {manifest['version']} - AGGIORNAMENTO INTRANET\n\n"
            "Su una postazione dotata della funzione: accedere come ADMIN, aprire\n"
            "Impostazioni > Aggiornamenti e backup > Aggiorna tramite intranet,\n"
            "poi Installa e riavvia. Non serve Internet.\n\n"
            "Per la prima adozione su versioni prive del pulsante: chiudere l'app,\n"
            "aprire PowerShell nella cartella locale del programma ed eseguire:\n"
            '.\\.venv\\Scripts\\python.exe "\\\\srvshare\\lab_dati\\SOFTWARE_DATI\\Strumenti\\aggiorna_intranet.py" .\n'
            "Confermare con SI dopo la verifica. Il bootstrap usa gli stessi\n"
            "backup e rollback automatici e installa le dipendenze offline.\n"
            "Serve un'installazione da pacchetto con .tools/uv.exe e Python 3.11-3.13.\n\n"
            "Non estrarre strumenti-dependencies nella cartella del programma.\n"
            "ZIP e singoli file sono verificati con SHA-256 dal manifest.\n"
            "La condivisione deve essere scrivibile solo da chi pubblica il software.\n"
            "I backup restano locali in .updates; nessun database è distribuito.\n",
            encoding="utf-8")
        (staging / "SHA256SUMS.txt").write_text("".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in sorted(staging.iterdir()) if path.is_file()), encoding="utf-8")
        os.rename(staging, output)
    except BaseException:
        shutil.rmtree(staging)
        raise
    return output / "update-manifest.json"


if __name__ == "__main__":
    main()
