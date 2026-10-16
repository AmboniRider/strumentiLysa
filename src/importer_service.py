# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modulo Servizio di Importazione File Strumenti.

Orchestra la scansione della cartella di ingresso, l'invocazione dei driver,
la validazione dei codici campione, la persistenza su database SQLite e
lo spostamento fisico dei file nelle cartelle di archivio o errore.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Set

from driver import get_driver
from src.config import AppConfig
from src.database import Database
from src.models import ParsedSample, SampleRecord
from src.validator import validate_sample_code


@dataclass
class ImportItemResult:
    """Rappresenta l'esito dell'importazione di un singolo campione (o file)."""
    filepath: Path
    filename: str
    sample_code: str = ""
    status: str = "PENDING"  # SUCCESS, MERGED, DUPLICATE, ERROR, SKIPPED, INFO
    message: str = ""
    parsed_sample: Optional[ParsedSample] = None
    unmapped_params: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ImportBatchSummary:
    """Riepilogo complessivo di una sessione di importazione."""
    total_files_found: int = 0
    imported_count: int = 0
    merged_count: int = 0
    duplicate_count: int = 0
    error_count: int = 0
    skipped_count: int = 0
    items: List[ImportItemResult] = field(default_factory=list)
    unmapped_params_global: Set[str] = field(default_factory=set)
    warnings: List[str] = field(default_factory=list)
    messages: List[str] = field(default_factory=list)


class ImporterService:
    """Servizio per la scansione ed elaborazione dei file generati dagli strumenti."""

    def __init__(self, db: Database):
        self.db = db

    def scan_input_directory(self, input_dir: Path | str) -> List[Path]:
        """Cerca tutti i file di testo (.txt, .csv, .dat) presenti nella cartella di ingresso."""
        dir_path = Path(input_dir)
        if not dir_path.is_dir():
            return []
        files = []
        for ext in ("*.txt", "*.TXT", "*.csv", "*.CSV", "*.dat", "*.DAT"):
            files.extend(list(dir_path.glob(ext)))
        return sorted(list(set(files)), key=lambda p: p.name)

    def process_file_samples(
        self,
        filepath: Path,
        config: AppConfig,
        overwrite: bool = False,
        duplicate_callback: Optional[Callable[[str], bool]] = None
    ) -> List[ImportItemResult]:
        """Elabora tutti i campioni presenti in un file di sequenza analitica (singoli o multipli).

        Supporta sia file mono-campione (es. Dionex IC) sia file contenenti più campioni
        distinti (es. Mettler Toledo).
        """
        if not filepath.is_file():
            return [ImportItemResult(filepath=filepath, filename=filepath.name, status="ERROR", message="File non trovato")]

        # Esame e sostanza devono provenire dalla stessa lettura delle regole:
        # i driver continuano a ricevere la mappa di sole stringhe già supportata.
        rules_map = self.db.get_transcoding_rules_map(active_only=True)
        trans_map = {name: rule.lis_exam_code for name, rule in rules_map.items()}
        allowed_labs = config.allowed_labs_set

        # 1. Parsing tramite driver (estrae uno o più campioni)
        try:
            driver = get_driver(filepath, preferred_driver_name=config.default_driver)
            batch = driver.parse_batch(filepath, trans_map, allowed_labs=allowed_labs)
            parsed_samples = batch.samples
        except Exception as ex:
            self._move_file_to(filepath, config.error_dir)
            return [ImportItemResult(filepath=filepath, filename=filepath.name, status="ERROR", message=f"Errore durante il parsing del file: {ex}")]

        if not parsed_samples:
            if batch.archive_if_empty:
                self._move_file_to(filepath, config.archive_dir)
                return [ImportItemResult(
                    filepath=filepath, filename=filepath.name, status="INFO",
                    message="File archiviato senza campioni validi: soltanto controlli o identificativi ignorati",
                )]
            self._move_file_to(filepath, config.error_dir)
            return [ImportItemResult(
                filepath=filepath, filename=filepath.name, status="ERROR",
                message="Nessun dato analitico estratto dal file", warnings=batch.warnings,
            )]

        item_results: List[ImportItemResult] = []
        any_success_or_handled = False

        for parsed in parsed_samples:
            for result in parsed.results:
                rule = rules_map.get(result.param_name)
                result.lis_substance_code = rule.lis_substance_code if rule else None
            item = ImportItemResult(
                filepath=filepath,
                filename=filepath.name,
                sample_code=parsed.sample_code,
                parsed_sample=parsed,
            )

            # 2. Validazione del Codice Campione
            is_valid, val_code, val_msg = validate_sample_code(parsed.sample_code, allowed_labs)
            if not is_valid or val_code is None:
                item.status = "ERROR"
                item.message = f"Codice campione non valido ({parsed.sample_code}): {val_msg}"
                item_results.append(item)
                continue

            # Controllo parametri non mappati
            unmapped = [r.param_name for r in parsed.results if not r.is_mapped]
            item.unmapped_params = unmapped

            # 3. Salvataggio / Integrazione su database SQLite con Unione Intelligente (Merge)
            sample_rec = SampleRecord(
                id=None,
                sample_code=val_code.raw_code,
                lab_code=val_code.lab_code,
                year=val_code.year_4digit,
                acceptance=val_code.acceptance,
                conferment=val_code.conferment,
                sample_number=val_code.sample_number,
                source_filename=filepath.name,
            )

            exists = self.db.sample_exists(val_code.raw_code)

            if exists and not overwrite and duplicate_callback:
                user_wants = duplicate_callback(val_code.raw_code)
                if not user_wants:
                    item.status = "SKIPPED"
                    item.message = f"Campione {val_code.raw_code} saltato dall'utente"
                    item_results.append(item)
                    any_success_or_handled = True
                    continue

            ok, db_msg, _ = self.db.save_sample_with_results(
                sample=sample_rec,
                results=parsed.results,
                overwrite=overwrite,
                merge=True
            )

            if ok:
                if exists:
                    if "integrato" in db_msg.lower():
                        item.status = "MERGED"
                    else:
                        item.status = "DUPLICATE"
                else:
                    item.status = "SUCCESS"
                item.message = db_msg
                any_success_or_handled = True
            else:
                item.status = "ERROR"
                item.message = db_msg

            item_results.append(item)

        # 5. Gestione spostamento fisico del file:
        # Se almeno un campione è stato elaborato con successo o gestito dall'utente -> archivia
        # Se tutti i campioni sono falliti -> sposta in errori (a meno che non fossero solo duplicati saltati senza prompt)
        if any_success_or_handled:
            self._move_file_to(filepath, config.archive_dir)
        else:
            has_only_duplicates = all(r.status == "DUPLICATE" for r in item_results)
            if not has_only_duplicates:
                self._move_file_to(filepath, config.error_dir)

        # Le segnalazioni appartengono al file: agganciale una sola volta, senza
        # creare falsi campioni o modificare i conteggi di importazione/duplicati.
        item_results[0].warnings.extend(batch.warnings)
        return item_results

    def process_single_file(
        self,
        filepath: Path,
        config: AppConfig,
        overwrite: bool = False
    ) -> ImportItemResult:
        """Elabora un singolo file di sequenza analitica (metodo per retrocompatibilità)."""
        results = self.process_file_samples(filepath, config, overwrite=overwrite)
        return results[0] if results else ImportItemResult(
            filepath=filepath,
            filename=filepath.name,
            status="ERROR",
            message="Nessun dato elaborato"
        )

    def _move_file_to(self, src: Path, dest_dir: Path) -> Path:
        """Sposta in modo sicuro un file nella cartella di destinazione (gestendo conflitti di nome)."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / src.name
        if dest_file.exists():
            # Se esiste già un file con lo stesso nome nell'archivio, aggiungi timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest_file = dest_dir / f"{src.stem}_{timestamp}{src.suffix}"

        try:
            shutil.move(str(src), str(dest_file))
        except Exception:
            # Se move fallisce, prova copy + remove
            try:
                shutil.copy2(str(src), str(dest_file))
                src.unlink(missing_ok=True)
            except Exception:
                pass
        return dest_file

    def import_all(
        self,
        config: AppConfig,
        duplicate_callback: Optional[Callable[[str], bool]] = None
    ) -> ImportBatchSummary:
        """Esegue l'importazione batch di tutti i file presenti nella cartella di ingresso.

        Args:
            config: Configurazione attiva con i percorsi.
            duplicate_callback: Funzione opzionale richiamata per ogni duplicato che restituisce
                                True se l'utente desidera sovrascrivere, False altrimenti.
        """
        config.ensure_directories()
        files = self.scan_input_directory(config.input_dir)
        summary = ImportBatchSummary(total_files_found=len(files))

        for file_path in files:
            results = self.process_file_samples(
                file_path,
                config,
                overwrite=False,
                duplicate_callback=duplicate_callback,
            )

            for res in results:
                if res.status == "SUCCESS":
                    summary.imported_count += 1
                elif res.status == "MERGED":
                    summary.merged_count += 1
                elif res.status == "DUPLICATE":
                    summary.duplicate_count += 1
                elif res.status == "SKIPPED":
                    summary.skipped_count += 1
                elif res.status == "ERROR":
                    summary.error_count += 1
                elif res.status == "INFO":
                    summary.messages.append(f"{res.filename}: {res.message}")

                summary.warnings.extend(f"{res.filename}: {warning}" for warning in res.warnings)

                summary.items.append(res)
                if res.unmapped_params:
                    summary.unmapped_params_global.update(res.unmapped_params)

        return summary
