# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Genera un pacchetto aggiornamento senza database e il relativo manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tomllib
from zipfile import ZIP_DEFLATED, ZipFile

from src import __version__
from src.update_service import REPOSITORY, SCHEMA_VERSION, safe_runtime_path, validate_manifest
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
    args = parser.parse_args()
    print(build_release(Path(__file__).resolve().parent, args.output, args.mode, args.losses,
                        args.min_schema, args.max_schema))


if __name__ == "__main__":
    main()
