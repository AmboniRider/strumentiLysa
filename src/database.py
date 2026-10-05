# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modulo Database SQLite.

Gestisce la connessione al database SQLite locale, la creazione e migrazione
delle tabelle, il seed iniziale dei dati e tutte le operazioni CRUD per
campioni, risultati, utenti, transcodifiche e configurazioni.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

from src.auth import generate_salt, hash_password
from src.config import (
    DEFAULT_APP_VERSION,
    DEFAULT_DB_PATH,
    DEFAULT_DRIVER_NAME,
    DEFAULT_LAB_CODES,
    DEFAULT_PATHS,
    DEFAULT_TRANSCODINGS,
    AppConfig,
)
from src.models import ParsedResult, SampleFilter, SampleRecord, TranscodingRule, UserRecord


class Database:
    """Gestore dell'accesso e delle operazioni sul database SQLite."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Crea e restituisce una connessione al database con Row factory, gestendone commit e chiusura."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Crea le tabelle del database se non esistono e popola i dati di default."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Tabella Utenti
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('ADMIN', 'OPERATORE')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_login DATETIME
                )
            """)

            # 2. Tabella Configurazioni
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS configurations (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Tabella Transcodifiche
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcodings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_param_name TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    lis_exam_code TEXT NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Tabella Campioni
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_code TEXT UNIQUE NOT NULL COLLATE NOCASE,
                    lab_code TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    acceptance TEXT NOT NULL,
                    conferment INTEGER NOT NULL,
                    sample_number INTEGER NOT NULL,
                    source_filename TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'DA_ESPORTARE' CHECK(status IN ('DA_ESPORTARE', 'ESPORTATO', 'ERRORE')),
                    imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    exported_at DATETIME,
                    export_filename TEXT
                )
            """)

            # Indice su sample_code e data importazione
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_code ON samples(sample_code)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_imported_at ON samples(imported_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_samples_status ON samples(status)")

            # 5. Tabella Risultati Parametri Campione
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sample_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id INTEGER NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
                    param_name TEXT NOT NULL,
                    raw_value TEXT NOT NULL,
                    numeric_value REAL,
                    formatted_value TEXT NOT NULL,
                    lis_exam_code TEXT,
                    is_mapped INTEGER DEFAULT 1,
                    is_exported INTEGER DEFAULT 0,
                    exported_at DATETIME
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_sample_id ON sample_results(sample_id)")

            # Migrazione automatica colonne is_exported e exported_at su database esistenti
            cursor.execute("PRAGMA table_info(sample_results)")
            existing_cols = {row["name"] for row in cursor.fetchall()}
            if "is_exported" not in existing_cols:
                cursor.execute("ALTER TABLE sample_results ADD COLUMN is_exported INTEGER DEFAULT 0")
                cursor.execute("""
                    UPDATE sample_results SET is_exported = 1
                    WHERE sample_id IN (SELECT id FROM samples WHERE status = 'ESPORTATO')
                """)
            if "exported_at" not in existing_cols:
                cursor.execute("ALTER TABLE sample_results ADD COLUMN exported_at DATETIME")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_results_is_exported ON sample_results(is_exported)")

            # 6. Tabella Log di Audit
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

        # Esegui il seed iniziale
        self._seed_initial_data()

    def _seed_initial_data(self) -> None:
        """Popola l'utente admin di default, le transcodifiche e le configurazioni iniziali."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Seed Utente Admin
            cursor.execute("SELECT COUNT(*) AS cnt FROM users")
            if cursor.fetchone()["cnt"] == 0:
                salt = generate_salt()
                pwd_hash = hash_password("admin", salt)
                cursor.execute(
                    "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                    ("admin", pwd_hash, salt, "ADMIN")
                )

            # Seed Configurazioni Percorsi
            for key, val in DEFAULT_PATHS.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO configurations (key, value, description) VALUES (?, ?, ?)",
                    (key, val, f"Percorso cartella predefinita per {key}")
                )

            # Seed Codici Laboratorio
            cursor.execute(
                "INSERT OR IGNORE INTO configurations (key, value, description) VALUES (?, ?, ?)",
                ("allowed_labs", DEFAULT_LAB_CODES, "Codici identificativi laboratori abilitati separati da virgola")
            )

            # Seed Driver di Default
            cursor.execute(
                "INSERT OR IGNORE INTO configurations (key, value, description) VALUES (?, ?, ?)",
                ("default_driver", DEFAULT_DRIVER_NAME, "Nome dello strumento analitico / driver di default")
            )

            # Seed Versione Software
            cursor.execute(
                "INSERT OR IGNORE INTO configurations (key, value, description) VALUES (?, ?, ?)",
                ("app_version", DEFAULT_APP_VERSION, "Versione del software dell'applicazione")
            )

            # Seed Transcodifiche Iniziali
            for param, lis_code in DEFAULT_TRANSCODINGS.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO transcodings (instrument_param_name, lis_exam_code, description) VALUES (?, ?, ?)",
                    (param, lis_code, f"Mappatura di default per {param}")
                )

            conn.commit()

    # =========================================================================
    # GESTIONE CONFIGURAZIONI
    # =========================================================================

    def get_config(self) -> AppConfig:
        """Carica l'oggetto AppConfig corrente dal database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM configurations")
            rows = cursor.fetchall()
            cfg_dict = {row["key"]: row["value"] for row in rows}

            return AppConfig(
                input_dir=cfg_dict.get("path_input", DEFAULT_PATHS["path_input"]),
                archive_dir=cfg_dict.get("path_archive", DEFAULT_PATHS["path_archive"]),
                error_dir=cfg_dict.get("path_error", DEFAULT_PATHS["path_error"]),
                export_dir=cfg_dict.get("path_export", DEFAULT_PATHS["path_export"]),
                allowed_labs=cfg_dict.get("allowed_labs", DEFAULT_LAB_CODES),
                default_driver=cfg_dict.get("default_driver", DEFAULT_DRIVER_NAME),
                app_version=cfg_dict.get("app_version", DEFAULT_APP_VERSION),
            )

    def save_config_value(self, key: str, value: str, description: Optional[str] = None) -> None:
        """Salva o aggiorna una singola chiave di configurazione."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO configurations (key, value, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    description = COALESCE(excluded.description, configurations.description),
                    updated_at = CURRENT_TIMESTAMP
            """, (key, value, description))
            conn.commit()

    def save_all_configs(self, config: AppConfig) -> None:
        """Salva tutte le cartelle, codici laboratorio, driver e versione in configurazione."""
        self.save_config_value("path_input", str(config.input_dir))
        self.save_config_value("path_archive", str(config.archive_dir))
        self.save_config_value("path_error", str(config.error_dir))
        self.save_config_value("path_export", str(config.export_dir))
        self.save_config_value("allowed_labs", config.allowed_labs_str)
        self.save_config_value("default_driver", config.default_driver)
        self.save_config_value("app_version", config.app_version)

    # =========================================================================
    # GESTIONE UTENTI & AUTENTICAZIONE
    # =========================================================================

    def get_user_by_username(self, username: str) -> Optional[UserRecord]:
        """Cerca un utente per username (case-insensitive)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
            row = cursor.fetchone()
            if not row:
                return None
            return UserRecord(
                id=row["id"],
                username=row["username"],
                password_hash=row["password_hash"],
                salt=row["salt"],
                role=row["role"],
                created_at=row["created_at"],
                last_login=row["last_login"],
            )

    def update_user_last_login(self, user_id: int) -> None:
        """Aggiorna il timestamp di ultimo accesso dell'utente."""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (user_id,)
            )
            conn.commit()

    def get_all_users(self) -> List[UserRecord]:
        """Restituisce la lista di tutti gli utenti registrati."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY username ASC")
            return [
                UserRecord(
                    id=row["id"],
                    username=row["username"],
                    password_hash=row["password_hash"],
                    salt=row["salt"],
                    role=row["role"],
                    created_at=row["created_at"],
                    last_login=row["last_login"],
                )
                for row in cursor.fetchall()
            ]

    def add_user(self, username: str, password: str, role: str) -> tuple[bool, str]:
        """Crea un nuovo utente nel database."""
        clean_user = username.strip()
        role_clean = role.strip().upper()
        if not clean_user:
            return False, "Nome utente non valido"
        if role_clean not in ("ADMIN", "OPERATORE"):
            return False, "Ruolo non valido (consentiti: ADMIN, OPERATORE)"
        if not password:
            return False, "Password obbligatoria"

        salt = generate_salt()
        pwd_hash = hash_password(password, salt)

        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                    (clean_user, pwd_hash, salt, role_clean)
                )
                conn.commit()
            return True, f"Utente '{clean_user}' creato con successo"
        except sqlite3.IntegrityError:
            return False, f"L'utente '{clean_user}' esiste già"

    def update_user_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
        """Aggiorna la password di un utente."""
        if not new_password:
            return False, "Nuova password non valida"
        salt = generate_salt()
        pwd_hash = hash_password(new_password, salt)

        with self.get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (pwd_hash, salt, user_id)
            )
            conn.commit()
        return True, "Password aggiornata con successo"

    def update_user_role(self, user_id: int, new_role: str) -> tuple[bool, str]:
        """Aggiorna il ruolo di un utente."""
        role_clean = new_role.strip().upper()
        if role_clean not in ("ADMIN", "OPERATORE"):
            return False, "Ruolo non valido"

        with self.get_connection() as conn:
            conn.execute("UPDATE users SET role = ? WHERE id = ?", (role_clean, user_id))
            conn.commit()
        return True, "Ruolo utente aggiornato"

    def delete_user(self, user_id: int, current_user_id: int) -> tuple[bool, str]:
        """Elimina un utente (impedisce l'auto-eliminazione e l'eliminazione dell'ultimo admin)."""
        if user_id == current_user_id:
            return False, "Non puoi eliminare il tuo stesso account"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False, "Utente non trovato"

            if row["role"] == "ADMIN":
                cursor.execute("SELECT COUNT(*) AS admin_count FROM users WHERE role = 'ADMIN'")
                if cursor.fetchone()["admin_count"] <= 1:
                    return False, "Impossibile eliminare l'unico utente Amministratore rimasto"

            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
        return True, "Utente eliminato con successo"

    # =========================================================================
    # GESTIONE TRANSCODIFICHE
    # =========================================================================

    def get_transcoding_map(self, active_only: bool = True) -> Dict[str, str]:
        """Restituisce un dizionario {parametro_strumento: codice_lis}."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT instrument_param_name, lis_exam_code FROM transcodings"
            if active_only:
                query += " WHERE is_active = 1"
            cursor.execute(query)
            return {row["instrument_param_name"]: row["lis_exam_code"] for row in cursor.fetchall()}

    def get_all_transcodings(self) -> List[TranscodingRule]:
        """Restituisce tutte le regole di transcodifica."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transcodings ORDER BY instrument_param_name ASC")
            return [
                TranscodingRule(
                    id=row["id"],
                    instrument_param_name=row["instrument_param_name"],
                    lis_exam_code=row["lis_exam_code"],
                    description=row["description"] or "",
                    is_active=bool(row["is_active"]),
                    updated_at=row["updated_at"],
                )
                for row in cursor.fetchall()
            ]

    def save_transcoding(self, param_name: str, lis_code: str, description: str = "") -> tuple[bool, str]:
        """Aggiunge o aggiorna una regola di transcodifica."""
        param_clean = param_name.strip()
        lis_clean = lis_code.strip().upper()
        if not param_clean or not lis_clean:
            return False, "Parametro e Codice LIS sono obbligatori"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transcodings (instrument_param_name, lis_exam_code, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(instrument_param_name) DO UPDATE SET
                    lis_exam_code = excluded.lis_exam_code,
                    description = excluded.description,
                    is_active = 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (param_clean, lis_clean, description.strip()))
            conn.commit()
        return True, f"Regola per '{param_clean}' salvata con successo"

    def delete_transcoding(self, transcoding_id: int) -> tuple[bool, str]:
        """Elimina una regola di transcodifica."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM transcodings WHERE id = ?", (transcoding_id,))
            conn.commit()
        return True, "Regola eliminata con successo"

    def update_transcoding(
        self,
        transcoding_id: int,
        param_name: str,
        lis_code: str,
        description: str = ""
    ) -> tuple[bool, str]:
        """Modifica una regola di transcodifica esistente identificata da ID.

        Verifica che i campi obbligatori siano compilati e che il nome del parametro
        non entri in collisione con un'altra regola già registrata a database.
        """
        param_clean = param_name.strip()
        lis_clean = lis_code.strip().upper()
        if not param_clean or not lis_clean:
            return False, "Parametro e Codice LIS sono obbligatori"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM transcodings WHERE id = ?", (transcoding_id,))
            if not cursor.fetchone():
                return False, "Regola di transcodifica non trovata"

            cursor.execute(
                "SELECT id FROM transcodings WHERE instrument_param_name = ? COLLATE NOCASE AND id != ?",
                (param_clean, transcoding_id)
            )
            if cursor.fetchone():
                return False, f"Esiste già una regola per il parametro '{param_clean}'"

            cursor.execute("""
                UPDATE transcodings
                SET instrument_param_name = ?,
                    lis_exam_code = ?,
                    description = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (param_clean, lis_clean, description.strip(), transcoding_id))
            conn.commit()

        return True, f"Regola per '{param_clean}' aggiornata con successo"

    # =========================================================================
    # GESTIONE CAMPIONI E RISULTATI
    # =========================================================================

    def sample_exists(self, sample_code: str) -> bool:
        """Verifica se un campione con il dato codice è già presente a database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM samples WHERE sample_code = ?", (sample_code.strip(),))
            return cursor.fetchone() is not None

    def save_sample_with_results(
        self,
        sample: SampleRecord,
        results: List[ParsedResult],
        overwrite: bool = False,
        merge: bool = False
    ) -> tuple[bool, str, Optional[int]]:
        """Salva un campione e i suoi parametri nel database.

        Se il campione esiste già:
          - Se merge=True, esegue l'unione intelligente (Merge):
            * Inserisce i nuovi parametri con is_exported=0.
            * Aggiorna i valori dei parametri esistenti preservando lo stato is_exported
              (nessun re-invio automatico al LIS di test già esportati in precedenza).
            * Aggiorna lo stato del campione a 'DA_ESPORTARE' se ci sono parametri pendenti,
              oppure a 'ESPORTATO' se tutti risultano già inviati.
          - Se merge=False e overwrite=False, ritorna (False, msg, sample_id).
          - Se merge=False e overwrite=True, cancella e ricrea tutti i risultati.
        """
        clean_code = sample.sample_code.strip().upper()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, status FROM samples WHERE sample_code = ?", (clean_code,))
            existing = cursor.fetchone()

            if existing:
                sample_id = existing["id"]

                if not merge and not overwrite:
                    return False, f"Campione {clean_code} già presente nel database", sample_id

                if not merge and overwrite:
                    cursor.execute("""
                        UPDATE samples SET
                            lab_code = ?, year = ?, acceptance = ?, conferment = ?,
                            sample_number = ?, source_filename = ?, status = 'DA_ESPORTARE',
                            imported_at = CURRENT_TIMESTAMP, exported_at = NULL, export_filename = NULL
                        WHERE id = ?
                    """, (
                        sample.lab_code, sample.year, sample.acceptance, sample.conferment,
                        sample.sample_number, sample.source_filename, sample_id
                    ))
                    cursor.execute("DELETE FROM sample_results WHERE sample_id = ?", (sample_id,))
                    for res in results:
                        cursor.execute("""
                            INSERT INTO sample_results (
                                sample_id, param_name, raw_value, numeric_value,
                                formatted_value, lis_exam_code, is_mapped, is_exported
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                        """, (
                            sample_id, res.param_name, res.raw_value, res.numeric_value,
                            res.formatted_value, res.lis_exam_code, 1 if res.is_mapped else 0
                        ))
                    conn.commit()
                    return True, f"Campione {clean_code} sovrascritto con {len(results)} parametri", sample_id

                # =============================================================
                # UNIONE INTELLIGENTE (MERGE)
                # =============================================================
                cursor.execute("""
                    SELECT id, param_name, raw_value, formatted_value, is_exported
                    FROM sample_results WHERE sample_id = ?
                """, (sample_id,))
                existing_results = {row["param_name"].strip().upper(): row for row in cursor.fetchall()}

                new_params_count = 0
                updated_params_count = 0

                for res in results:
                    key = res.param_name.strip().upper()
                    if key in existing_results:
                        old_row = existing_results[key]
                        cursor.execute("""
                            UPDATE sample_results SET
                                raw_value = ?,
                                numeric_value = ?,
                                formatted_value = ?,
                                lis_exam_code = ?,
                                is_mapped = ?
                            WHERE id = ?
                        """, (
                            res.raw_value,
                            res.numeric_value,
                            res.formatted_value,
                            res.lis_exam_code,
                            1 if res.is_mapped else 0,
                            old_row["id"]
                        ))
                        if old_row["formatted_value"] != res.formatted_value:
                            updated_params_count += 1
                    else:
                        cursor.execute("""
                            INSERT INTO sample_results (
                                sample_id, param_name, raw_value, numeric_value,
                                formatted_value, lis_exam_code, is_mapped, is_exported
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                        """, (
                            sample_id,
                            res.param_name,
                            res.raw_value,
                            res.numeric_value,
                            res.formatted_value,
                            res.lis_exam_code,
                            1 if res.is_mapped else 0,
                        ))
                        new_params_count += 1

                # Verifica se ci sono parametri ancora da esportare
                cursor.execute("SELECT COUNT(*) AS cnt FROM sample_results WHERE sample_id = ? AND is_exported = 0", (sample_id,))
                pending_cnt = cursor.fetchone()["cnt"]

                new_status = "DA_ESPORTARE" if pending_cnt > 0 else "ESPORTATO"

                cursor.execute("""
                    UPDATE samples SET
                        source_filename = ?,
                        status = ?,
                        imported_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (sample.source_filename, new_status, sample_id))

                conn.commit()

                if new_params_count > 0 or updated_params_count > 0:
                    msg = f"Campione {clean_code} integrato: +{new_params_count} nuovi test, {updated_params_count} aggiornati"
                else:
                    msg = f"Campione {clean_code} già registrato (nessun nuovo dato)"
                return True, msg, sample_id

            else:
                # Inserimento nuovo campione
                cursor.execute("""
                    INSERT INTO samples (
                        sample_code, lab_code, year, acceptance, conferment,
                        sample_number, source_filename, status, imported_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'DA_ESPORTARE', CURRENT_TIMESTAMP)
                """, (
                    clean_code,
                    sample.lab_code,
                    sample.year,
                    sample.acceptance,
                    sample.conferment,
                    sample.sample_number,
                    sample.source_filename,
                ))
                sample_id = cursor.lastrowid

                for res in results:
                    cursor.execute("""
                        INSERT INTO sample_results (
                            sample_id, param_name, raw_value, numeric_value,
                            formatted_value, lis_exam_code, is_mapped, is_exported
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    """, (
                        sample_id,
                        res.param_name,
                        res.raw_value,
                        res.numeric_value,
                        res.formatted_value,
                        res.lis_exam_code,
                        1 if res.is_mapped else 0,
                    ))

                conn.commit()
                return True, f"Campione {clean_code} salvato con {len(results)} parametri", sample_id

    def get_samples(self, filter_opts: Optional[SampleFilter] = None) -> List[SampleRecord]:
        """Estrae la lista dei campioni applicando i filtri di ricerca, stato e temporali."""
        opts = filter_opts or SampleFilter()
        query = """
            SELECT s.*,
                   COUNT(r.id) AS results_count,
                   SUM(CASE WHEN r.is_exported = 0 THEN 1 ELSE 0 END) AS pending_results_count
            FROM samples s
            LEFT JOIN sample_results r ON s.id = r.sample_id
            WHERE 1=1
        """
        params: List[Any] = []

        # 1. Filtro di Stato
        if opts.status_filter == "DA_ESPORTARE":
            query += " AND s.status = 'DA_ESPORTARE'"
        elif opts.status_filter == "ESPORTATI":
            query += " AND s.status = 'ESPORTATO'"

        # 2. Filtro Temporale (Default 'MESE' = ultimi 30 giorni)
        now = datetime.now()
        if opts.date_filter == "SETTIMANA":
            dt_from = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
            query += " AND s.imported_at >= ?"
            params.append(dt_from)
        elif opts.date_filter == "MESE":
            dt_from = (now - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
            query += " AND s.imported_at >= ?"
            params.append(dt_from)
        elif opts.date_filter == "TRE_MESI":
            dt_from = (now - timedelta(days=90)).strftime("%Y-%m-%d 00:00:00")
            query += " AND s.imported_at >= ?"
            params.append(dt_from)
        elif opts.date_filter == "ANNO":
            dt_from = datetime(now.year, 1, 1).strftime("%Y-%m-%d 00:00:00")
            query += " AND s.imported_at >= ?"
            params.append(dt_from)
        elif opts.date_filter == "PERSONALIZZATO":
            if opts.custom_date_from:
                query += " AND s.imported_at >= ?"
                params.append(opts.custom_date_from.strftime("%Y-%m-%d 00:00:00"))
            if opts.custom_date_to:
                query += " AND s.imported_at <= ?"
                params.append(opts.custom_date_to.strftime("%Y-%m-%d 23:59:59"))
        # 'TUTTI' non aggiunge vincoli temporali

        # 3. Ricerca Testuale (sample_code, acceptance, lab_code, filename)
        if opts.search_query.strip():
            q = f"%{opts.search_query.strip()}%"
            query += " AND (s.sample_code LIKE ? OR s.acceptance LIKE ? OR s.lab_code LIKE ? OR s.source_filename LIKE ?)"
            params.extend([q, q, q, q])

        query += " GROUP BY s.id ORDER BY s.imported_at DESC, s.sample_code ASC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()

            return [
                SampleRecord(
                    id=row["id"],
                    sample_code=row["sample_code"],
                    lab_code=row["lab_code"],
                    year=row["year"],
                    acceptance=row["acceptance"],
                    conferment=row["conferment"],
                    sample_number=row["sample_number"],
                    source_filename=row["source_filename"],
                    status=row["status"],
                    imported_at=row["imported_at"],
                    exported_at=row["exported_at"],
                    export_filename=row["export_filename"],
                    results_count=row["results_count"],
                    pending_results_count=row["pending_results_count"] or 0,
                )
                for row in rows
            ]

    def get_sample_results(self, sample_id: int) -> List[ParsedResult]:
        """Restituisce tutti i risultati/parametri associati ad un campione."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sample_results WHERE sample_id = ? ORDER BY id ASC
            """, (sample_id,))
            return [
                ParsedResult(
                    param_name=row["param_name"],
                    raw_value=row["raw_value"],
                    numeric_value=row["numeric_value"] if row["numeric_value"] is not None else 0.0,
                    formatted_value=row["formatted_value"],
                    lis_exam_code=row["lis_exam_code"],
                    is_mapped=bool(row["is_mapped"]),
                    id=row["id"],
                    is_exported=bool(row["is_exported"]) if "is_exported" in row.keys() else False,
                    exported_at=row["exported_at"] if "exported_at" in row.keys() else None,
                )
                for row in cursor.fetchall()
            ]

    def get_sample_with_results(self, sample_id: int) -> Optional[SampleRecord]:
        """Restituisce un campione completo dei suoi parametri."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM samples WHERE id = ?", (sample_id,))
            row = cursor.fetchone()
            if not row:
                return None

            results = self.get_sample_results(sample_id)
            pending_cnt = sum(1 for r in results if not r.is_exported)
            return SampleRecord(
                id=row["id"],
                sample_code=row["sample_code"],
                lab_code=row["lab_code"],
                year=row["year"],
                acceptance=row["acceptance"],
                conferment=row["conferment"],
                sample_number=row["sample_number"],
                source_filename=row["source_filename"],
                status=row["status"],
                imported_at=row["imported_at"],
                exported_at=row["exported_at"],
                export_filename=row["export_filename"],
                results_count=len(results),
                pending_results_count=pending_cnt,
                results=results,
            )

    def mark_samples_as_exported(self, sample_ids: List[int], export_filename: str) -> None:
        """Aggiorna lo stato dei campioni e di tutti i loro parametri a ESPORTATO."""
        if not sample_ids:
            return
        placeholders = ",".join("?" for _ in sample_ids)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.get_connection() as conn:
            conn.execute(f"""
                UPDATE sample_results SET
                    is_exported = 1,
                    exported_at = ?
                WHERE sample_id IN ({placeholders})
            """, [now_str, *sample_ids])
            conn.execute(f"""
                UPDATE samples SET
                    status = 'ESPORTATO',
                    exported_at = ?,
                    export_filename = ?
                WHERE id IN ({placeholders})
            """, [now_str, export_filename, *sample_ids])
            conn.commit()

    def mark_results_as_exported(
        self,
        result_ids: List[int],
        sample_ids: List[int],
        export_filename: str
    ) -> None:
        """Aggiorna lo stato dei singoli parametri esportati a is_exported = 1.

        Ricalcola lo stato dei campioni coinvolti:
        - Se tutti i parametri di un campione sono ora esportati, il campione passa a 'ESPORTATO'.
        - Se ha ancora parametri con is_exported = 0, il campione rimane 'DA_ESPORTARE'.
        """
        if not sample_ids and not result_ids:
            return
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Aggiorna lo stato dei singoli parametri selezionati
            if result_ids:
                placeholders = ",".join("?" for _ in result_ids)
                cursor.execute(f"""
                    UPDATE sample_results SET
                        is_exported = 1,
                        exported_at = ?
                    WHERE id IN ({placeholders})
                """, [now_str, *result_ids])

            # 2. Ricalcola lo stato per ciascun campione coinvolto
            for s_id in set(sample_ids):
                cursor.execute("""
                    SELECT COUNT(*) AS pending
                    FROM sample_results
                    WHERE sample_id = ? AND is_exported = 0
                """, (s_id,))
                row = cursor.fetchone()
                pending = row["pending"] if row else 0

                if pending == 0:
                    cursor.execute("""
                        UPDATE samples SET
                            status = 'ESPORTATO',
                            exported_at = ?,
                            export_filename = ?
                        WHERE id = ?
                    """, (now_str, export_filename, s_id))
                else:
                    cursor.execute("""
                        UPDATE samples SET
                            status = 'DA_ESPORTARE'
                        WHERE id = ?
                    """, (s_id,))

            conn.commit()

    def get_summary_counts(self) -> dict[str, int]:
        """Restituisce i conteggi aggregati (totale, da esportare, esportati)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'DA_ESPORTARE' THEN 1 ELSE 0 END) AS da_esportare,
                    SUM(CASE WHEN status = 'ESPORTATO' THEN 1 ELSE 0 END) AS esportati
                FROM samples
            """)
            row = cursor.fetchone()
            return {
                "total": row["total"] or 0,
                "da_esportare": row["da_esportare"] or 0,
                "esportati": row["esportati"] or 0,
            }

    # =========================================================================
    # MANUTENZIONE E PULIZIA CAMPIONI ESPORTATI (SOLO ADMIN)
    # =========================================================================

    def get_exported_samples_from_date(self, from_date: datetime | str) -> List[SampleRecord]:
        """Restituisce l'elenco dei campioni già esportati aventi data di esportazione
        a partire dalla data specificata (>= data ore 00:00:00).

        Args:
            from_date: Data di inizio (datetime o stringa YYYY-MM-DD o DD/MM/YYYY).

        Returns:
            Lista di SampleRecord con il conteggio dei parametri associati.
        """
        cutoff = self._parse_cutoff_date(from_date)
        query = """
            SELECT s.*, COUNT(r.id) AS results_count
            FROM samples s
            LEFT JOIN sample_results r ON s.id = r.sample_id
            WHERE s.status = 'ESPORTATO'
              AND COALESCE(s.exported_at, s.imported_at) >= ?
            GROUP BY s.id
            ORDER BY COALESCE(s.exported_at, s.imported_at) ASC, s.id ASC
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (cutoff,))
            rows = cursor.fetchall()
            return [
                SampleRecord(
                    id=row["id"],
                    sample_code=row["sample_code"],
                    lab_code=row["lab_code"],
                    year=row["year"],
                    acceptance=row["acceptance"],
                    conferment=row["conferment"],
                    sample_number=row["sample_number"],
                    source_filename=row["source_filename"],
                    status=row["status"],
                    imported_at=row["imported_at"],
                    exported_at=row["exported_at"],
                    export_filename=row["export_filename"],
                    results_count=row["results_count"],
                )
                for row in rows
            ]

    def delete_exported_samples_from_date(
        self,
        from_date: datetime | str,
        current_user: UserRecord
    ) -> tuple[bool, str, int]:
        """Elimina dal database tutti i campioni già esportati a partire da una data specificata.

        Operazione strettamente riservata agli utenti con ruolo Amministratore (ADMIN).
        I risultati analitici correlati nella tabella 'sample_results' vengono eliminati
        automaticamente tramite vincolo CASCADE. I file fisici archiviati su disco vengono preservati.

        Args:
            from_date: Data iniziale (datetime o stringa).
            current_user: Utente autenticato che esegue l'operazione (deve essere ADMIN).

        Returns:
            Tupla (successo: bool, messaggio: str, numero_campioni_eliminati: int).
        """
        if not current_user or current_user.role.upper() != "ADMIN":
            return False, "Accesso negato: operazione consentita esclusivamente agli utenti Amministratori.", 0

        try:
            cutoff = self._parse_cutoff_date(from_date)
        except ValueError as e:
            return False, str(e), 0

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Recupera gli ID dei campioni che soddisfano il criterio
            cursor.execute("""
                SELECT id FROM samples
                WHERE status = 'ESPORTATO'
                  AND COALESCE(exported_at, imported_at) >= ?
            """, (cutoff,))
            rows = cursor.fetchall()
            count = len(rows)

            if count == 0:
                return True, f"Nessun campione esportato trovato a partire dalla data {cutoff[:10]}.", 0

            sample_ids = [r["id"] for r in rows]
            placeholders = ",".join("?" for _ in sample_ids)

            # 2. Eliminazione campioni (i parametri in sample_results vengono rimossi da FK cascade)
            cursor.execute(f"DELETE FROM samples WHERE id IN ({placeholders})", sample_ids)
            conn.commit()

        # 3. Registrazione evento nel log di audit
        display_date = cutoff[:10]
        self.log_action(
            current_user.id,
            current_user.username,
            "DELETE_EXPORTED_SAMPLES",
            f"Eliminati {count} campioni esportati a partire dal {display_date}"
        )

        return True, f"Eliminati con successo {count} campioni esportati a partire dal {display_date}.", count

    @staticmethod
    def _parse_cutoff_date(date_val: datetime | str) -> str:
        """Normalizza una data (datetime o stringa) nel formato SQLite 'YYYY-MM-DD 00:00:00'.

        Supporta formati comuni come 'YYYY-MM-DD', 'DD/MM/YYYY', 'DD-MM-YYYY' e timestamp completi.
        """
        if isinstance(date_val, datetime):
            return date_val.strftime("%Y-%m-%d 00:00:00")

        s = str(date_val).strip()
        if not s:
            raise ValueError("La data di riferimento non può essere vuota.")

        # Estrai la sola componente data se presente orario
        date_part = s.split(" ")[0]

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(date_part, fmt)
                return dt.strftime("%Y-%m-%d 00:00:00")
            except ValueError:
                continue

        for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M:%S"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue

        raise ValueError(f"Formato data '{date_val}' non riconosciuto. Usare AAAA-MM-GG o GG/MM/AAAA.")

    # =========================================================================
    # AUDIT LOGS
    # =========================================================================

    def log_action(self, user_id: Optional[int], username: str, action: str, details: str = "") -> None:
        """Registra un evento nel log di audit."""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO audit_logs (user_id, username, action, details) VALUES (?, ?, ?, ?)",
                    (user_id, username, action, details)
                )
                conn.commit()
        except Exception:
            pass

