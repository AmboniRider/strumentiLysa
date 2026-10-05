# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modulo di Esportazione CSV per il LIS (Laboratory Information System).

Genera file CSV strutturati secondo il tracciato record fisso a 24 colonne
richiesto dal LIS e aggiorna lo stato dei campioni esportati nel database.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from src.database import Database
from src.models import SampleRecord

# Intestazione standard a 24 colonne fisse
LIS_CSV_HEADER = [
    "ANNO",
    "ACCETTAZIONE",
    "CONFERIMENTO",
    "CAMPIONE",
    "ALIQUOTA",
    "UNITÀ CAMPIONARIA",
    "N. RISULTATO",
    "SEGNO",
    "VALORE",
    "RISULTATO",
    "TIPO ESAME",
    "ESITO",
    "UNITÀ BGSURA",
    "DATA INIZIO",
    "DATA FINE",
    "SOSTANZA",
    "RISULTATO SOSTANZA",
    "VALORE SOSTANZA",
    "SEGNO SOSTANZA",
    "INCERTEZZA SOSTANZA",
    "GERME",
    "RILEVATO GERME",
    "VALORE GERME",
    "CODICE CAMPIONE",
]


class LISExporter:
    """Generatore del tracciato CSV per il LIS."""

    def __init__(self, db: Database):
        self.db = db

    def generate_export_filename(self) -> str:
        """Genera il nome file standard con timestamp: ESPORTAZIONE_YYYYMMDD_HHMMSS.csv."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"ESPORTAZIONE_{timestamp}.csv"

    def export_samples(
        self,
        samples: List[SampleRecord],
        target_dir: Path | str,
        custom_filename: str | None = None
    ) -> Tuple[bool, str, Path, int]:
        """Esporta una lista di campioni nel formato CSV standard del LIS.

        Args:
            samples: Lista di SampleRecord da esportare (con i relativi parametri).
            target_dir: Cartella di destinazione (default: ./export).
            custom_filename: Opzionale nome file specifico.

        Returns:
            Tuple (success: bool, message: str, file_path: Path, rows_exported: int)
        """
        if not samples:
            return False, "Nessun campione selezionato per l'esportazione", Path(), 0

        out_dir = Path(target_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        filename = custom_filename or self.generate_export_filename()
        filepath = out_dir / filename

        rows_written = 0
        exported_sample_ids: List[int] = []

        try:
            # Apri il file con codifica UTF-8
            with open(filepath, "w", encoding="utf-8", newline="\r\n") as f:
                # 1. Scrivi intestazione con separatore ';'
                f.write(";".join(LIS_CSV_HEADER) + "\n")

                # 2. Scrivi le righe per ogni parametro di ciascun campione
                exported_result_ids: List[int] = []
                for s in samples:
                    # Usa i parametri presenti nell'oggetto (es. selezione parziale) o caricali dal DB
                    results = s.results if s.results is not None else (self.db.get_sample_results(s.id) if s.id is not None else [])
                    if not results:
                        continue

                    if s.id is not None:
                        exported_sample_ids.append(s.id)

                    for r in results:
                        if r.id is not None:
                            exported_result_ids.append(r.id)

                        # Se il parametro non ha codice LIS, usa il nome parametro o segnala
                        tipo_esame = r.lis_exam_code if r.lis_exam_code else r.param_name

                        # Valorizza le 24 colonne
                        row = [
                            str(s.year),                  # ANNO (4 cifre)
                            str(s.acceptance),            # ACCETTAZIONE
                            str(s.conferment),            # CONFERIMENTO (senza zeri)
                            str(s.sample_number),         # CAMPIONE (senza zeri)
                            "",                           # ALIQUOTA
                            "",                           # UNITÀ CAMPIONARIA
                            "",                           # N. RISULTATO
                            "",                           # SEGNO
                            str(r.formatted_value),       # VALORE (virgola o '0')
                            "",                           # RISULTATO
                            tipo_esame,                   # TIPO ESAME (es. BG00594)
                            "",                           # ESITO
                            "",                           # UNITÀ BGSURA
                            "",                           # DATA INIZIO
                            "",                           # DATA FINE
                            "",                           # SOSTANZA
                            "",                           # RISULTATO SOSTANZA
                            "",                           # VALORE SOSTANZA
                            "",                           # SEGNO SOSTANZA
                            "",                           # INCERTEZZA SOSTANZA
                            "",                           # GERME
                            "",                           # RILEVATO GERME
                            "",                           # VALORE GERME
                            s.sample_code,                # CODICE CAMPIONE (18 car.)
                        ]
                        f.write(";".join(row) + "\n")
                        rows_written += 1

            if rows_written == 0:
                filepath.unlink(missing_ok=True)
                return False, "Nessun parametro selezionato per l'esportazione", filepath, 0

            # 3. Aggiorna lo stato dei parametri e ricalcola lo stato dei campioni nel database
            if exported_result_ids:
                self.db.mark_results_as_exported(exported_result_ids, exported_sample_ids, filename)
            elif exported_sample_ids:
                self.db.mark_samples_as_exported(exported_sample_ids, filename)

            msg = f"Esportati {len(exported_sample_ids)} campioni ({rows_written} righe analitiche) nel file '{filename}'"
            return True, msg, filepath, rows_written

        except Exception as ex:
            return False, f"Errore durante la generazione del file CSV: {ex}", filepath, 0
