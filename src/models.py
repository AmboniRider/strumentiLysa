# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modelli dati e strutture per l'interfaccia Strumenti-LIS.

Questo modulo definisce le dataclass utilizzate per rappresentare campioni,
risultati analitici, regole di transcodifica, utenti e opzioni di filtro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ParsedResult:
    """Rappresenta il singolo parametro analitico estratto da un file di strumento."""
    param_name: str
    raw_value: str
    numeric_value: float
    formatted_value: str
    lis_exam_code: Optional[str] = None
    is_mapped: bool = False
    id: Optional[int] = None
    is_exported: bool = False
    exported_at: Optional[str] = None
    # Snapshot della transcodifica: una modifica alle regole non cambia lo storico.
    lis_substance_code: Optional[str] = None


@dataclass
class ParsedSample:
    """Rappresenta un campione analitico completo estratto da un file di strumento."""
    sample_code: str
    source_filename: str
    results: list[ParsedResult] = field(default_factory=list)
    instrument_name: str = "Cromatografo Ionico (Dionex / IC)"


@dataclass
class ParsedBatch:
    """Esito del parsing completo, prima di qualsiasi salvataggio.

    samples contiene i campioni acquisibili; warnings descrive righe scartate.
    archive_if_empty distingue un file valido di soli controlli da un fallimento.
    Il default mantiene la gestione dei file vuoti dei driver preesistenti.
    """
    samples: list[ParsedSample] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    archive_if_empty: bool = False


@dataclass
class SampleRecord:
    """Rappresenta un record della tabella 'samples' salvato nel database SQLite."""
    id: Optional[int]
    sample_code: str
    lab_code: str
    year: int
    acceptance: str
    conferment: int
    sample_number: int
    source_filename: str
    status: str = "DA_ESPORTARE"  # 'DA_ESPORTARE', 'ESPORTATO', 'ERRORE'
    imported_at: Optional[str] = None
    exported_at: Optional[str] = None
    export_filename: Optional[str] = None
    results_count: int = 0
    pending_results_count: int = 0
    results: list[ParsedResult] = field(default_factory=list)


@dataclass
class UserRecord:
    """Rappresenta un utente del sistema."""
    id: Optional[int]
    username: str
    password_hash: str
    salt: str
    role: str  # 'ADMIN' o 'OPERATORE'
    created_at: Optional[str] = None
    last_login: Optional[str] = None


@dataclass
class TranscodingRule:
    """Rappresenta una regola di transcodifica tra parametro strumento e codice esame LIS."""
    id: Optional[int]
    instrument_param_name: str
    lis_exam_code: str
    description: str = ""
    is_active: bool = True
    updated_at: Optional[str] = None
    lis_substance_code: Optional[str] = None


@dataclass
class SampleFilter:
    """Opzioni di filtro per la ricerca campioni nella GUI."""
    search_query: str = ""
    status_filter: str = "TUTTI"  # 'TUTTI', 'DA_ESPORTARE', 'ESPORTATI'
    date_filter: str = "MESE"     # 'SETTIMANA', 'MESE', 'TRE_MESI', 'ANNO', 'TUTTI'
    custom_date_from: Optional[datetime] = None
    custom_date_to: Optional[datetime] = None
