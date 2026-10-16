# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modulo di Esportazione CSV per il LIS (Laboratory Information System).

Genera file CSV strutturati secondo il tracciato record fisso a 24 colonne
richiesto dal LIS e aggiorna lo stato dei campioni esportati nel database.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

from src.auth import SessionManager
from src.database import Database
from src.models import ParsedResult, SampleRecord

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

    def _prepare_export(
        self, samples: List[SampleRecord],
    ) -> tuple[list[tuple[SampleRecord, list[ParsedResult]]], list[str]]:
        """Filtra gli esami incompleti prima di creare file o aggiornare stati.

        La completezza dipende dal catalogo attivo corrente, mentre i codici
        delle righe restano quelli salvati all'importazione. Gli standard non
        partecipano al controllo delle sostanze e mantengono il loro flusso.
        """
        catalog: dict[str, set[str]] = {}
        for rule in self.db.get_transcoding_rules_map().values():
            if rule.lis_substance_code is not None:
                catalog.setdefault(rule.lis_exam_code, set()).add(rule.lis_substance_code)

        prepared: list[tuple[SampleRecord, list[ParsedResult]]] = []
        warnings: list[str] = []
        for sample in samples:
            # I risultati forniti dal chiamante costituiscono la selezione.
            # Nessun ripiego su tutti gli esami del DB se la lista manca o è vuota.
            results = sample.results or []
            groups: dict[str, list[ParsedResult]] = {}
            for result in results:
                if result.lis_substance_code:
                    groups.setdefault(result.lis_exam_code or "", []).append(result)

            invalid_exams: set[str] = set()
            for exam, selected_results in groups.items():
                expected = catalog.get(exam, set())
                counts = Counter(r.lis_substance_code for r in selected_results)
                selected = set(counts)
                reasons: list[str] = []
                if not expected:
                    reasons.append("nessun catalogo sostanze attivo per questo esame")
                else:
                    missing_selection = expected - selected
                    if missing_selection:
                        # Questa lettura distingue sostanze non ancora acquisite
                        # da sostanze presenti che l'operatore ha deselezionato.
                        available = self.db.get_sample_results(sample.id) if sample.id is not None else results
                        present = {r.lis_substance_code for r in available if r.lis_exam_code == exam}
                        missing = missing_selection - present
                        unselected = missing_selection & present
                        if missing:
                            reasons.append("sostanze mancanti: " + ", ".join(sorted(missing)))
                        if unselected:
                            reasons.append("sostanze non selezionate: " + ", ".join(sorted(unselected)))
                unexpected = selected - expected
                if unexpected:
                    reasons.append("sostanze fuori catalogo: " + ", ".join(sorted(unexpected)))
                duplicates = {code for code, count in counts.items() if count > 1}
                if duplicates:
                    reasons.append("sostanze duplicate: " + ", ".join(sorted(duplicates)))
                if reasons:
                    invalid_exams.add(exam)
                    warnings.append(f"Campione {sample.sample_code}, esame {exam or '(senza codice LIS)'}: " + "; ".join(reasons))

            accepted = [r for r in results if not r.lis_substance_code or (r.lis_exam_code or "") not in invalid_exams]
            if accepted:
                prepared.append((sample, accepted))
        return prepared, warnings

    def export_samples(
        self,
        samples: List[SampleRecord],
        target_dir: Path | str,
        custom_filename: str | None = None
    ) -> Tuple[bool, str, Path, int]:
        """Esporta una lista di campioni nel formato CSV standard del LIS.

        Args:
            samples: Campioni con i soli parametri selezionati in results.
                Una lista results vuota o assente non esporta alcun esame.
            target_dir: Cartella di destinazione (default: ./export).
            custom_filename: Opzionale nome file specifico.

        Returns:
            Tuple (success: bool, message: str, file_path: Path, rows_exported: int)
        """
        if not samples:
            return False, "Nessun campione selezionato per l'esportazione", Path(), 0

        filename = custom_filename or self.generate_export_filename()
        filepath = Path(target_dir) / filename

        rows_written = 0
        exported_sample_ids: List[int] = []

        try:
            prepared, warnings = self._prepare_export(samples)
            warning_text = "\n\nEsami saltati (nessuna loro sostanza esportata):\n" + "\n".join(warnings) if warnings else ""
            if warnings:
                user = SessionManager.get_user()
                self.db.log_action(user.id if user else None, user.username if user else "sistema",
                                   "EXPORT_LIS_SKIPPED", "\n".join(warnings))
            if not prepared:
                return False, "Nessun parametro esportabile" + warning_text, filepath, 0

            filepath.parent.mkdir(parents=True, exist_ok=True)
            # Apri il file con codifica UTF-8
            with open(filepath, "w", encoding="utf-8", newline="\r\n") as f:
                # 1. Scrivi intestazione con separatore ';'
                f.write(";".join(LIS_CSV_HEADER) + "\n")

                # 2. Scrivi le righe per ogni parametro di ciascun campione
                exported_result_ids: List[int] = []
                for s, results in prepared:
                    if s.id is not None:
                        exported_sample_ids.append(s.id)

                    # Alcuni chiamanti usano ancora i risultati del driver senza
                    # ID. Risolviamo solo corrispondenze univoche al DB: marcare
                    # l'intero campione includerebbe anche esami appena esclusi.
                    persisted = self.db.get_sample_results(s.id) if s.id is not None and any(r.id is None for r in results) else []

                    for r in results:
                        if r.id is not None:
                            exported_result_ids.append(r.id)
                        elif persisted:
                            matches = [p for p in persisted if p.param_name == r.param_name
                                       and p.lis_exam_code == r.lis_exam_code
                                       and p.lis_substance_code == r.lis_substance_code
                                       and p.formatted_value == r.formatted_value]
                            if len(matches) == 1 and matches[0].id is not None:
                                exported_result_ids.append(matches[0].id)

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
                            "" if r.lis_substance_code else str(r.formatted_value),  # VALORE solo standard
                            "",                           # RISULTATO
                            tipo_esame,                   # TIPO ESAME (es. BG00594)
                            "",                           # ESITO
                            "",                           # UNITÀ BGSURA
                            "",                           # DATA INIZIO
                            "",                           # DATA FINE
                            r.lis_substance_code or "",    # SOSTANZA (codice esito LIS)
                            "",                           # RISULTATO SOSTANZA
                            str(r.formatted_value) if r.lis_substance_code else "",  # VALORE SOSTANZA
                            "",                           # SEGNO SOSTANZA
                            "",                           # INCERTEZZA SOSTANZA
                            "",                           # GERME
                            "",                           # RILEVATO GERME
                            "",                           # VALORE GERME
                            s.sample_code,                # CODICE CAMPIONE (18 car.)
                        ]
                        f.write(";".join(row) + "\n")
                        rows_written += 1

            # 3. Aggiorna lo stato dei parametri e ricalcola lo stato dei campioni nel database
            if exported_result_ids:
                self.db.mark_results_as_exported(exported_result_ids, exported_sample_ids, filename)

            msg = f"Esportati {len(prepared)} campioni ({rows_written} righe analitiche) nel file '{filename}'" + warning_text
            return True, msg, filepath, rows_written

        except Exception as ex:
            return False, f"Errore durante la generazione del file CSV: {ex}", filepath, 0
