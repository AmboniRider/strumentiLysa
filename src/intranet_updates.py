# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Lettura della distribuzione SMB e staging offline, senza accesso HTTP."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import re
from zipfile import BadZipFile, ZipFile

from src import __version__
from src.update_service import MAX_DOWNLOAD, Release, UpdateError, validate_manifest, version_tuple

INTRANET_DIRECTORY = Path(r"\\srvshare\lab_dati\SOFTWARE_DATI\Strumenti")


def package_name(version: str) -> str:
    """Deriva un nome locale fisso dalla versione, mai da un percorso remoto."""
    version_tuple(version)
    return f"strumenti-update-{version}.zip"


def read_shared_file(path: Path, maximum: int) -> bytes:
    """Legge al massimo il limite indicato e segnala errori SMB comprensibili."""
    try:
        with path.open("rb") as stream:
            content = stream.read(maximum + 1)
        if len(content) > maximum:
            raise UpdateError("File intranet superiore al limite consentito")
        return content
    except OSError as exc:
        raise UpdateError(f"File intranet non accessibile: {path}. Verificare rete e permessi.") from exc


def validate_offline(manifest: dict) -> dict:
    """Richiede archivio e checksum delle dipendenze per impedire fallback Internet."""
    try:
        offline = manifest["offline"]
        if offline["package"] != f"strumenti-dependencies-{manifest['version']}.zip":
            raise ValueError("nome archivio dipendenze")
        if not re.fullmatch(r"[a-f0-9]{64}", offline["sha256"]):
            raise ValueError("checksum dipendenze")
        files = offline["files"]
        if not isinstance(files, dict) or "requirements.txt" not in files or len(files) < 2:
            raise ValueError("elenco dipendenze")
        for name, digest in files.items():
            if (name != "requirements.txt" and not re.fullmatch(r"[A-Za-z0-9_.+-]+\.whl", name)):
                raise ValueError("percorso dipendenza")
            if not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("checksum file dipendenza")
    except (KeyError, TypeError, ValueError) as exc:
        raise UpdateError(f"Manifest intranet offline non valido: {exc}") from exc
    return offline


def check_intranet_release(current: str = __version__, directory: Path = INTRANET_DIRECTORY) -> Release | None:
    """Legge il manifest condiviso e restituisce solo versioni stabili successive."""
    try:
        manifest = json.loads(read_shared_file(directory / "update-manifest.json", 1024 * 1024))
        validate_manifest(manifest, manifest["version"])
        validate_offline(manifest)
        if version_tuple(manifest["version"]) <= version_tuple(current):
            return None
        return Release(manifest["version"], str(manifest.get("notes", "")), str(directory), manifest, directory)
    except (KeyError, TypeError, ValueError) as exc:
        raise UpdateError("Manifest intranet non leggibile o incompleto") from exc


def stage_dependencies(release: Release, job: Path) -> None:
    """Copia e verifica tutte le wheel in locale prima della chiusura dell'app."""
    offline = validate_offline(release.manifest)
    content = read_shared_file(release.directory / offline["package"], MAX_DOWNLOAD)
    if hashlib.sha256(content).hexdigest() != offline["sha256"]:
        raise UpdateError("Checksum archivio dipendenze intranet errato")
    try:
        with ZipFile(io.BytesIO(content)) as archive:
            files = offline["files"]
            if len(archive.namelist()) != len(files) or set(archive.namelist()) != set(files):
                raise UpdateError("Archivio dipendenze con file inattesi")
            if sum(item.file_size for item in archive.infolist()) > MAX_DOWNLOAD:
                raise UpdateError("Dipendenze decompresse superiori al limite consentito")
            for name, digest in files.items():
                payload = archive.read(name)
                if hashlib.sha256(payload).hexdigest() != digest:
                    raise UpdateError(f"Dipendenza alterata: {name}")
                target = job / "dependencies" / name
                target.parent.mkdir(exist_ok=True)
                target.write_bytes(payload)
    except BadZipFile as exc:
        raise UpdateError("Archivio dipendenze intranet danneggiato") from exc
