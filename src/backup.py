# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Copie SQLite consistenti, senza modificare il database sorgente."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime
from pathlib import Path
import os
import sqlite3
import time


def validate_database(path: Path) -> None:
    """Rifiuta copie corrotte o con riferimenti orfani, aprendole in sola lettura."""
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Il database non supera il controllo di integrità")
        if conn.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Il database contiene riferimenti non validi")


def copy_database(source: Path, destination: Path, timeout: float = 30) -> Path:
    """Copia anche le pagine WAL committate, senza sovrascrivere file esistenti.

    La destinazione è riservata con O_EXCL prima di aprirla con SQLite; in caso
    di errore viene rimossa soltanto la copia incompleta creata dalla funzione.
    """
    source, destination = source.resolve(), destination.resolve()
    if source == destination:
        raise ValueError("Scegliere una destinazione diversa dal database attuale")
    fd = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    deadline = time.monotonic() + timeout

    def progress(status: int, remaining: int, total: int) -> None:
        """Limita l'attesa quando un altro processo mantiene occupato SQLite."""
        if time.monotonic() > deadline:
            raise TimeoutError("Database occupato: copia interrotta")

    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(destination)) as copied:
                original.backup(copied, pages=128, progress=progress, sleep=0.05)
        validate_database(destination)
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination


def dated_backup(source: Path, directory: Path) -> Path:
    """Crea una copia completa datata nella cartella scelta dall'amministratore."""
    name = f"strumenti_{datetime.now():%Y%m%d_%H%M%S_%f}.db"
    return copy_database(source, directory / name)
