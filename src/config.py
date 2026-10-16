# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modulo di Configurazione dell'Applicazione.

Fornisce costanti predefinite, gestione dei percorsi delle cartelle operative,
selezione del driver di default e utilità per caricare/salvare le configurazioni nel database SQLite.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Set

# Percorsi di base del progetto
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB_PATH = DATA_DIR / "strumenti.db"

# Cartelle operative predefinite
DEFAULT_PATHS = {
    "path_input": str(BASE_DIR / "sequenze"),
    "path_archive": str(BASE_DIR / "archiviati"),
    "path_error": str(BASE_DIR / "errori"),
    "path_export": str(BASE_DIR / "export"),
}

DEFAULT_LAB_CODES = "BG,MI,BS,RL,VP,MN,MB"
DEFAULT_DRIVER_NAME = "Cromatografo Ionico (Dionex / IC)"
DEFAULT_APP_VERSION = "1.1"

# Transcodifiche iniziali di default
DEFAULT_TRANSCODINGS: Dict[str, str] = {
    "Fluoruri": "BG00594",
    "Cloriti": "BG00589",
    "Cloruri": "BG00590",
    "Nitriti": "BG00596",
    "Clorati": "BG00588",
    "Nitrati": "BG00595",
    "Solfati": "BG00603",
}


class AppConfig:
    """Rappresenta le impostazioni operative correnti dell'applicazione."""

    def __init__(
        self,
        input_dir: str | Path = DEFAULT_PATHS["path_input"],
        archive_dir: str | Path = DEFAULT_PATHS["path_archive"],
        error_dir: str | Path = DEFAULT_PATHS["path_error"],
        export_dir: str | Path = DEFAULT_PATHS["path_export"],
        allowed_labs: str = DEFAULT_LAB_CODES,
        default_driver: str = DEFAULT_DRIVER_NAME,
        app_version: str = DEFAULT_APP_VERSION,
    ):
        self.input_dir = Path(input_dir)
        self.archive_dir = Path(archive_dir)
        self.error_dir = Path(error_dir)
        self.export_dir = Path(export_dir)
        self.allowed_labs_str = allowed_labs
        self.default_driver = default_driver
        self.app_version = str(app_version).strip() or DEFAULT_APP_VERSION

    @property
    def allowed_labs_set(self) -> Set[str]:
        return {code.strip().upper() for code in self.allowed_labs_str.split(",") if code.strip()}

    def ensure_directories(self) -> None:
        """Assicura che tutte le cartelle operative esistano sul filesystem."""
        for directory in (self.input_dir, self.archive_dir, self.error_dir, self.export_dir, DATA_DIR):
            directory.mkdir(parents=True, exist_ok=True)
