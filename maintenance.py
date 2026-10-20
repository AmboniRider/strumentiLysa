# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Preparazione e collaudo del database da parte del processo di aggiornamento."""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import json
import sqlite3
import sys

from src import __version__
from src.backup import copy_database, validate_database
from src.database import Database


def prepare_database(source: Path, target: Path, manifest: dict) -> None:
    """Migra una copia o recupera la configurazione su un nuovo database locale."""
    policy = manifest["database"]
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        schema = conn.execute("PRAGMA user_version").fetchone()[0]
    if not policy["min_schema"] <= schema <= policy["max_schema"]:
        raise ValueError("Schema sorgente incompatibile")
    if policy["mode"] != "reset":
        if policy["mode"] == "preserve" and schema != policy["target_schema"]:
            raise ValueError("Migrazione non dichiarata")
        copy_database(source, target)
    elif target.exists():
        raise FileExistsError(target)
    database = Database(target)
    if policy["mode"] == "reset":
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original:
            original.row_factory = sqlite3.Row
            with database.get_connection() as new:
                new.execute("BEGIN IMMEDIATE")
                for table in ("users", "configurations", "transcodings"):
                    columns = [row[1] for row in original.execute(f"PRAGMA table_info({table})")]
                    available = {row[1] for row in new.execute(f"PRAGMA table_info({table})")}
                    if not set(columns).issubset(available):
                        raise ValueError(f"Impossibile conservare integralmente {table}")
                    rows = [tuple(row) for row in original.execute(f"SELECT * FROM {table}")]
                    new.execute(f"DELETE FROM {table}")
                    quoted = ",".join('"' + col.replace('"', '""') + '"' for col in columns)
                    marks = ",".join("?" for _ in columns)
                    new.executemany(f"INSERT INTO {table} ({quoted}) VALUES ({marks})", rows)
                    recovered = [tuple(row) for row in new.execute(f"SELECT {quoted} FROM {table}")]
                    if sorted(recovered, key=repr) != sorted(rows, key=repr):
                        raise ValueError(f"Recupero incompleto: {table}")
                # Conservare anche i contatori evita di riutilizzare ID di
                # account o canali cancellati in precedenza sulla postazione.
                for table in ("users", "transcodings"):
                    sequence = original.execute("SELECT seq FROM sqlite_sequence WHERE name = ?", (table,)).fetchone()
                    if sequence:
                        new.execute("UPDATE sqlite_sequence SET seq = MAX(seq, ?) WHERE name = ?", (sequence[0], table))
    with database.get_connection() as conn:
        if conn.execute("PRAGMA user_version").fetchone()[0] != policy["target_schema"]:
            raise ValueError("Schema ottenuto diverso da quello dichiarato")
        # Un file candidato autonomo può essere sostituito senza dipendere dal WAL.
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    validate_database(target)


def probe(database_path: Path, expected_version: str) -> None:
    """Esegue il vero avvio GUI nascosto prima di confermare l'installazione."""
    if __version__ != expected_version:
        raise ValueError("Versione installata non corrispondente alla Release")
    from src.gui.app_window import AppWindow
    db = Database(database_path)
    app = AppWindow(db, check_updates=False)
    try:
        app.withdraw()
        app.update_idletasks()
        if not app.current_view:
            raise ValueError("Schermata di accesso non inizializzata")
    finally:
        app.destroy()
    validate_database(database_path)


def main() -> None:
    """Comandi interni: preparazione copia e controllo avvio, con banner console."""
    from app import init_terminal
    init_terminal("STRUMENTI LYSA - VERIFICA AGGIORNAMENTO")
    if sys.argv[1] == "prepare":
        prepare_database(Path(sys.argv[2]), Path(sys.argv[3]), json.loads(Path(sys.argv[4]).read_text(encoding="utf-8")))
    elif sys.argv[1] == "probe":
        probe(Path(sys.argv[2]), sys.argv[3])
    else:
        raise ValueError("Comando di manutenzione sconosciuto")


if __name__ == "__main__":
    main()
