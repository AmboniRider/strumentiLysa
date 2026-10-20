# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Contratto delle Release e download verificati, indipendenti dalla GUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import hashlib
import json
import re
import os
import platform
import shutil
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zipfile import ZipFile

from src import __version__, DATABASE_SCHEMA_VERSION

REPOSITORY = "AmboniRider/strumentiLysa"
API = f"https://api.github.com/repos/{REPOSITORY}/releases"
SCHEMA_VERSION = DATABASE_SCHEMA_VERSION
MAX_DOWNLOAD = 100 * 1024 * 1024
# Elenco esplicito: un aggiornamento non può sovrascrivere dati o strumenti locali.
ROOT_FILES = {"app.py", "driver.py", "pyproject.toml", "uv.lock", "LICENSE",
              "strumenti.ico", "manuale.md", "progetto.md", "transfer.md",
              "update_runner.py", "maintenance.py", "UPDATES.md", "LEGAL.md", "strumenti.bat"}


class UpdateError(Exception):
    """Errore di aggiornamento da presentare senza impedire l'uso ordinario."""


def version_tuple(value: str) -> tuple[int, int, int]:
    """Confronta versioni stabili numeriche; 1.10 è successivo a 1.9."""
    if not isinstance(value, str) or not re.fullmatch(r"v?\d+\.\d+(?:\.\d+)?", value):
        raise UpdateError("Versione stabile non valida")
    parts = tuple(int(part) for part in value.removeprefix("v").split("."))
    return (*parts, 0) if len(parts) == 2 else parts


def safe_runtime_path(name: str) -> bool:
    """Ammette solo sorgenti runtime e documentazione, senza percorsi traversali."""
    path = PurePosixPath(name)
    if not name or "\\" in name or ":" in name or str(path) != name:
        return False
    if any(part in (".", "..", "__pycache__") or part.startswith(".") for part in path.parts):
        return False
    return name in ROOT_FILES or (
        len(path.parts) > 1 and
        ((path.parts[0] == "src" and path.suffix == ".py") or
         (path.parts[0] == "driver_implementati" and path.suffix == ".md"))
    )


def trusted_url(url: str) -> bool:
    """I pacchetti devono appartenere alle Release del repository configurato."""
    parsed = urlparse(url)
    return (parsed.scheme == "https" and parsed.netloc == "github.com" and
            parsed.path.startswith(f"/{REPOSITORY}/releases/download/"))


def download(url: str, maximum: int = MAX_DOWNLOAD) -> bytes:
    """Scarica con timeout e limiti di dimensione, senza credenziali locali."""
    request = Request(url, headers={"User-Agent": "StrumentiLysa-Updater", "Accept": "application/vnd.github+json"})
    chunks: list[bytes] = []
    size = 0
    deadline = time.monotonic() + 10
    with urlopen(request, timeout=10) as response:
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError("Timeout durante il controllo o download")
            chunk = response.read(min(65536, maximum + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > maximum:
                raise UpdateError("Download superiore al limite consentito")
            chunks.append(chunk)
    return b"".join(chunks)


@dataclass(frozen=True)
class Release:
    """Release verificabile e politica esplicita di compatibilità del database."""

    version: str
    notes: str
    url: str
    manifest: dict

    @property
    def database_message(self) -> str:
        """Descrive gli effetti sui dati prima del consenso dell'amministratore."""
        mode = self.manifest["database"]["mode"]
        return {
            "preserve": "Database conservato: nessuna perdita di dati.",
            "migrate": "Migrazione del database senza perdita di dati.",
            "reset": "DATABASE NUOVO: perdita di campioni, risultati e audit. "
                     "Recupero di utenti, impostazioni e transcodifiche.\n" + self.manifest["database"]["losses"],
        }[mode]


def validate_manifest(data: dict, expected_version: str) -> dict:
    """Blocca metadati incompleti o incompatibili prima di scaricare il runtime."""
    try:
        if data["format"] != 1 or version_tuple(data["version"]) != version_tuple(expected_version):
            raise ValueError("versione manifest")
        py = data["python"]
        minimum, maximum = tuple(py["min"]), tuple(py["max_exclusive"])
        if (len(minimum) != 2 or len(maximum) != 2 or
                not all(type(n) is int for n in (*minimum, *maximum)) or
                not minimum <= sys.version_info[:2] < maximum):
            raise ValueError("versione Python non compatibile: installazione manuale necessaria")
        database = data["database"]
        mode = database["mode"]
        if mode not in ("preserve", "migrate", "reset"):
            raise ValueError("politica database")
        lower, upper, target = (database[k] for k in ("min_schema", "max_schema", "target_schema"))
        if not all(type(n) is int and n >= 0 for n in (lower, upper, target)) or lower > upper or target < upper:
            raise ValueError("intervallo schema")
        if mode == "reset" and not database.get("losses", "").strip():
            raise ValueError("descrizione perdita dati obbligatoria")
        package = data["package"]
        if not trusted_url(package["url"]) or not re.fullmatch("[a-f0-9]{64}", package["sha256"]):
            raise ValueError("pacchetto non valido")
        files = data["files"]
        if (not isinstance(files, dict) or not ROOT_FILES.issubset(files) or
                not {"src/__init__.py", "src/database.py", "src/update_service.py", "src/backup.py"}.issubset(files) or
                any(not safe_runtime_path(name) or not re.fullmatch("[a-f0-9]{64}", digest)
                    for name, digest in files.items())):
            raise ValueError("elenco file non valido")
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise UpdateError(f"Manifest non valido o incompatibile: {exc}") from exc
    return data


def check_release(current: str = __version__) -> Release | None:
    """Consulta solo Release pubblicate stabili; nessun risultato è un caso normale."""
    try:
        releases = json.loads(download(API, 2 * 1024 * 1024))
        candidates = []
        for entry in releases:
            if entry.get("draft") or entry.get("prerelease"):
                continue
            try:
                parsed = version_tuple(entry["tag_name"])
            except (KeyError, UpdateError):
                continue
            if parsed > version_tuple(current):
                candidates.append((parsed, entry))
        if not candidates:
            return None
        entry = max(candidates, key=lambda pair: pair[0])[1]
        asset = next((a for a in entry.get("assets", []) if a["name"] == "update-manifest.json"), None)
        if asset is None or not trusted_url(asset["browser_download_url"]):
            raise UpdateError("La nuova Release non contiene un manifest di aggiornamento valido")
        manifest = validate_manifest(json.loads(download(asset["browser_download_url"], 1024 * 1024)), entry["tag_name"])
        return Release(manifest["version"], entry.get("body") or "", entry["html_url"], manifest)
    except UpdateError:
        raise
    except Exception as exc:
        raise UpdateError("Impossibile verificare GitHub. Controllare la connessione e riprovare.") from exc


def stage_release(release: Release, root: Path, schema: int, reset_confirmed: bool = False) -> Path:
    """Scarica in un'area isolata e verifica ogni file prima di chiudere l'app."""
    if (root / ".git").exists():
        raise UpdateError("Copia di sviluppo: usare sync.bat o il flusso Git del progetto")
    if os.name != "nt" or platform.machine().lower() not in ("amd64", "x86_64"):
        raise UpdateError("L'installazione automatica richiede Windows x64")
    policy = release.manifest["database"]
    if not policy["min_schema"] <= schema <= policy["max_schema"]:
        raise UpdateError("Schema database non supportato da questa Release")
    if policy["mode"] == "preserve" and schema != policy["target_schema"]:
        raise UpdateError("La Release richiede una migrazione non dichiarata")
    if policy["mode"] == "reset" and not reset_confirmed:
        raise UpdateError("Sostituzione database non confermata")
    validate_manifest(release.manifest, release.version)
    if not (root / ".tools/uv.exe").is_file():
        raise UpdateError("Installazione senza uv locale: eseguire l'installazione manuale")
    database_size = sum(path.stat().st_size for path in (root / "data").glob("strumenti.db*") if path.is_file())
    environment_size = sum(path.stat().st_size for path in (root / ".venv").rglob("*") if path.is_file())
    needed = max(1024 * 1024 * 1024, database_size * 3 + environment_size * 2 + MAX_DOWNLOAD * 3)
    if shutil.disk_usage(root).free < needed:
        raise UpdateError(f"Spazio insufficiente: servono almeno {needed // (1024 * 1024)} MB liberi")
    import uuid
    job = root / ".updates" / uuid.uuid4().hex
    job.mkdir(parents=True)
    try:
        payload = download(release.manifest["package"]["url"])
        if hashlib.sha256(payload).hexdigest() != release.manifest["package"]["sha256"]:
            raise UpdateError("Checksum del pacchetto errato")
        archive_path = job / "package.zip"
        archive_path.write_bytes(payload)
        files = release.manifest["files"]
        with ZipFile(archive_path) as archive:
            if len(archive.namelist()) != len(files) or set(archive.namelist()) != set(files):
                raise UpdateError("Il pacchetto contiene file inattesi")
            if sum(item.file_size for item in archive.infolist()) > MAX_DOWNLOAD:
                raise UpdateError("Pacchetto decompresso troppo grande")
            for name, digest in files.items():
                content = archive.read(name)
                if hashlib.sha256(content).hexdigest() != digest:
                    raise UpdateError(f"File alterato: {name}")
                target = job / "payload" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        (job / "manifest.json").write_text(json.dumps(release.manifest), encoding="utf-8")
        # Il runner in uso resta eseguibile anche mentre si sostituisce il runtime.
        shutil.copyfile(root / "update_runner.py", job / "runner.py")
    except BaseException:
        shutil.rmtree(job)
        raise
    return job
