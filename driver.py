# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modulo Driver per Strumenti di Laboratorio.

Questo modulo isola interamente la logica di lettura, parsing e conversione
dei file generati dagli strumenti di laboratorio nel formato standard dell'applicazione.
I nuovi strumenti estendono questo modulo; configurazione, documentazione e test
completano l'integrazione nell'applicazione.
"""

from __future__ import annotations

import csv
import io
import math
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set, Type

from src.models import ParsedBatch, ParsedResult, ParsedSample
from src.validator import validate_sample_code


class BaseInstrumentDriver(ABC):
    """Classe base astratta per tutti i driver di strumenti di laboratorio."""

    name: str = "Base Instrument Driver"

    @abstractmethod
    def can_handle(self, file_path: Path | str) -> bool:
        """Verifica se il file specificato è compatibile con questo driver."""
        pass

    @abstractmethod
    def parse_file(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None
    ) -> ParsedSample:
        """Estrae i dati del campione e l'elenco dei risultati analitici dal file."""
        pass

    def parse_samples(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None
    ) -> List[ParsedSample]:
        """Estrae l'elenco di tutti i campioni presenti nel file.

        L'implementazione predefinita supporta i driver a campione singolo
        restituendo una lista contenente l'unico ParsedSample estratto da parse_file.
        I driver multi-campione (es. Mettler Toledo) possono sovrascrivere questo metodo.
        """
        sample = self.parse_file(file_path, transcode_map)
        return [sample] if sample else []

    def parse_batch(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None,
        allowed_labs: Optional[Set[str]] = None,
    ) -> ParsedBatch:
        """Adatta i driver esistenti all'esito batch senza cambiarne il parsing.

        allowed_labs serve ai driver che distinguono campioni e controlli durante
        la lettura; per gli altri resta attiva la validazione nel servizio.
        """
        return ParsedBatch(samples=self.parse_samples(file_path, transcode_map))

    @staticmethod
    def _read_text_file(path: Path) -> str:
        """Legge un file di testo provando le codifiche più comuni (utf-8, cp1252, latin-1).

        Elimina automaticamente eventuali byte nulli (`\\x00` / NUL) dovuti a padding
        di buffer a lunghezza fissa esportati da alcuni strumenti di laboratorio (es. Dionex IC).
        """
        encodings = ["utf-8-sig", "utf-8", "cp1252", "latin-1", "iso-8859-1"]
        for enc in encodings:
            try:
                content = path.read_text(encoding=enc)
                # Rimozione trasparente dei byte nulli di padding
                return content.replace("\x00", "")
            except (UnicodeDecodeError, LookupError):
                continue
        # Fallback con sostituzione caratteri non validi e rimozione byte nulli
        return path.read_text(encoding="utf-8", errors="replace").replace("\x00", "")

    @staticmethod
    def _normalize_value(raw_val: str) -> tuple[float, str]:
        """Normalizza un valore grezzo:

        - Se non numerico (es. 'n.a.', 'ND', vuoto) -> (0.0, "0")
        - Se numerico -> (valore_float, "valore_con_virgola")
        """
        cleaned = raw_val.strip()
        if not cleaned or cleaned.lower() in ("n.a.", "na", "n/a", "nd", "n.d.", "-", "null", "none"):
            return 0.0, "0"

        # Sostituisci la virgola con il punto per il parsing float
        normalized_str = cleaned.replace(",", ".")
        try:
            val_float = float(normalized_str)
            # Se è esattamente zero o intero, restituiamo comunque il formato coerente con virgola
            # Se la stringa originale aveva virgola, manteniamo il numero di cifre decimali originali
            if "," in cleaned:
                formatted = cleaned
            elif "." in cleaned:
                formatted = cleaned.replace(".", ",")
            else:
                formatted = cleaned
            return val_float, formatted
        except ValueError:
            return 0.0, "0"


class DionexICDriver(BaseInstrumentDriver):
    """Driver per Cromatografo Ionico (Dionex / IC).

    Struttura attesa:
    - Riga 1: 'Sample Name:\\t<CODICE_CAMPIONE>'
    - Righe 9-11: Intestazioni e spaziatori ('Component\\tAmount')
    - Righe 12+: 'NomeParametro\\tValore'
    """

    name: str = "Cromatografo Ionico (Dionex / IC)"

    def can_handle(self, file_path: Path | str) -> bool:
        path = Path(file_path)
        if not path.is_file():
            return False
        try:
            content = self._read_text_file(path)
            lines = content.splitlines()
            if not lines:
                return False
            # Verifica presenza di 'Sample Name:' nella prima riga o nei metadati iniziali
            first_lines = "\n".join(lines[:5])
            if "Sample Name:" in first_lines:
                return True
            return False
        except Exception:
            return False

    def parse_file(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None
    ) -> ParsedSample:
        path = Path(file_path)
        content = self._read_text_file(path)
        lines = content.splitlines()

        sample_code = ""
        results: List[ParsedResult] = []
        trans_map = transcode_map or {}

        # 1. Estrazione del Codice Campione
        for line in lines[:8]:
            if "Sample Name:" in line:
                parts = line.split("Sample Name:")
                if len(parts) > 1:
                    raw_name = parts[1].strip()
                    # Rimuovi eventuali tabulazioni o spazi extra
                    sample_code = raw_name.split("\t")[0].strip()
                break

        # Fallback: se non trovato con etichetta, prova dal nome del file (senza estensione)
        if not sample_code:
            sample_code = path.stem.strip()

        # 2. Individuazione della sezione dei dati / componenti
        start_parsing = False
        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue

            # Se incontriamo l'intestazione della tabella componenti
            if "Component" in line and "Amount" in line:
                start_parsing = True
                continue

            if start_parsing:
                # Splitta per tabulazione
                cols = line.split("\t")
                if len(cols) >= 2:
                    param_name = cols[0].strip()
                    raw_val = cols[1].strip()
                    if param_name:
                        num_val, fmt_val = self._normalize_value(raw_val)
                        lis_code = trans_map.get(param_name)
                        results.append(
                            ParsedResult(
                                param_name=param_name,
                                raw_value=raw_val,
                                numeric_value=num_val,
                                formatted_value=fmt_val,
                                lis_exam_code=lis_code,
                                is_mapped=bool(lis_code),
                            )
                        )

        return ParsedSample(
            sample_code=sample_code,
            source_filename=path.name,
            results=results,
            instrument_name=self.name,
        )



class SpectrophotometerDriver(BaseInstrumentDriver):
    """Driver per Spettrofotometro / Analizzatore UV-Vis.

    Struttura supportata: file di testo o CSV con formato chiave-valore o tabulare
    per letture di assorbanza e concentrazione analitica.
    """

    name: str = "Spettrofotometro (UV-Vis / Assorbanza)"

    def can_handle(self, file_path: Path | str) -> bool:
        path = Path(file_path)
        if not path.is_file():
            return False
        try:
            content = self._read_text_file(path)
            lines = content.splitlines()
            if not lines:
                return False
            # Riconosce intestazioni tipiche di spettrofotometri (es. Wavelength, Absorbance, UV, ecc.)
            header_text = "\n".join(lines[:10]).lower()
            return "absorbance" in header_text or "wavelength" in header_text or "uv-vis" in header_text
        except Exception:
            return False

    def parse_file(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None
    ) -> ParsedSample:
        path = Path(file_path)
        content = self._read_text_file(path)
        lines = content.splitlines()

        sample_code = path.stem.strip()
        results: List[ParsedResult] = []
        trans_map = transcode_map or {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Splitta per tab, virgola o punto e virgola
            delimiter = "\t" if "\t" in line else (";" if ";" in line else ",")
            cols = line.split(delimiter)
            if len(cols) >= 2:
                param_name = cols[0].strip()
                raw_val = cols[1].strip()
                if param_name.lower() in ("sample", "component", "parametro", "wavelength"):
                    continue
                num_val, fmt_val = self._normalize_value(raw_val)
                lis_code = trans_map.get(param_name)
                results.append(
                    ParsedResult(
                        param_name=param_name,
                        raw_value=raw_val,
                        numeric_value=num_val,
                        formatted_value=fmt_val,
                        lis_exam_code=lis_code,
                        is_mapped=bool(lis_code),
                    )
                )

        return ParsedSample(
            sample_code=sample_code,
            source_filename=path.name,
            results=results,
            instrument_name=self.name,
        )


class MettlerToledoDriver(BaseInstrumentDriver):
    """Driver per analizzatore / titolatore Mettler Toledo.

    Caratteristiche:
    - Riconoscimento tramite nome file contenente 'ListReport' e intestazioni (ID campione 1, Titolo, Risultato)
    - Supporto per file multi-campione (più campioni nello stesso file)
    - Separatore: ';'
    - Riga 1 e 2: metadati/titoli da ignorare
    - Riga 3: intestazione colonne
    - Righe 4+: dati analitici con ID Campione 1 (18 car.), Titolo (parametro), Risultato (valore)
    - Rimozione automatica delle unità di misura dal Risultato (es. '293,370 uS' -> '293,370')
    """

    name: str = "Mettler Toledo"

    def can_handle(self, file_path: Path | str) -> bool:
        path = Path(file_path)
        if not path.is_file():
            return False
        # Verifica che il nome file contenga 'listreport' (case-insensitive)
        if "listreport" not in path.name.lower():
            return False
        try:
            content = self._read_text_file(path)
            lines = content.splitlines()
            if len(lines) < 3:
                return False
            # Controllo presenza delle intestazioni attese nelle prime 5 righe
            header_found = False
            for line in lines[:5]:
                line_lower = line.lower()
                if "id campione 1" in line_lower and "titolo" in line_lower and "risultato" in line_lower:
                    header_found = True
                    break
            return header_found
        except Exception:
            return False

    @staticmethod
    def _extract_numeric_result(raw_val: str) -> tuple[float, str]:
        """Normalizza il risultato estraendo esclusivamente la componente numerica:

        - Rimuove completamente qualsiasi unità di misura o suffisso (es. '293,370 uS' -> 293.37, '293,370')
        - Sostituisce la virgola con il punto per il parsing float in Python
        - Restituisce formatted_value e raw_value sanitizzati con virgola decimale per il LIS
        """
        cleaned = raw_val.strip()
        if not cleaned or cleaned.lower() in ("n.a.", "na", "n/a", "nd", "n.d.", "-", "null", "none"):
            return 0.0, "0"

        # Cerca la prima sequenza numerica (inclusi eventuale segno e decimali con punto o virgola)
        match = re.search(r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?", cleaned)
        if not match:
            return 0.0, "0"

        num_str = match.group(0)
        try:
            # Per il float Python serve il punto decimale
            float_val = float(num_str.replace(",", "."))
            # Per il tracciato LIS e la visualizzazione serve la virgola decimale
            if "." in num_str and "," not in num_str:
                formatted_str = num_str.replace(".", ",")
            else:
                formatted_str = num_str
            return float_val, formatted_str
        except ValueError:
            return 0.0, "0"

    def parse_samples(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None
    ) -> List[ParsedSample]:
        path = Path(file_path)
        content = self._read_text_file(path)
        lines = content.splitlines()

        trans_map = transcode_map or {}
        # Mappa preservando l'ordine: sample_code -> list[ParsedResult]
        samples_dict: Dict[str, List[ParsedResult]] = {}

        # Salta le prime 3 righe (riga 1-2 saltare, riga 3 intestazione)
        for line in lines[3:]:
            line_str = line.strip()
            if not line_str:
                continue

            parts = [p.strip() for p in line.split(";")]
            if len(parts) < 3:
                continue

            sample_code = parts[0]
            param_name = parts[1]
            raw_res = parts[2]

            # Scarta righe senza codice campione o senza parametro/risultato (es. footer, timestamp)
            if not sample_code or not param_name or not raw_res:
                continue

            num_val, fmt_val = self._extract_numeric_result(raw_res)
            lis_code = trans_map.get(param_name)

            parsed_res = ParsedResult(
                param_name=param_name,
                raw_value=fmt_val,
                numeric_value=num_val,
                formatted_value=fmt_val,
                lis_exam_code=lis_code,
                is_mapped=bool(lis_code),
            )

            if sample_code not in samples_dict:
                samples_dict[sample_code] = []
            samples_dict[sample_code].append(parsed_res)

        parsed_samples: List[ParsedSample] = []
        for code, results in samples_dict.items():
            parsed_samples.append(
                ParsedSample(
                    sample_code=code,
                    source_filename=path.name,
                    results=results,
                    instrument_name=self.name,
                )
            )

        return parsed_samples

    def parse_file(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None
    ) -> ParsedSample:
        """Restituisce il primo campione estratto per compatibilità con l'interfaccia a singolo campione."""
        samples = self.parse_samples(file_path, transcode_map)
        if samples:
            return samples[0]
        return ParsedSample(
            sample_code=Path(file_path).stem,
            source_filename=Path(file_path).name,
            results=[],
            instrument_name=self.name,
        )


class Agilent5977CDriver(BaseInstrumentDriver):
    """Legge sequenze CSV Agilent: intestazione, riga ignorata, campioni/CQ.

    Ogni riga valida contiene un campione e un risultato per colonna esame.
    Il batch viene completato prima di restituire dati, così un CSV illeggibile
    o un'intestazione ambigua non provoca salvataggi parziali.
    """

    name: str = "Agilent 5977C"

    @staticmethod
    def _exam_name(header: str) -> str:
        """Toglie solo il suffisso finale Results, preservando il nome chimico."""
        return re.sub(r"\s+Results$", "", header.strip(), flags=re.IGNORECASE).strip()

    @staticmethod
    def _matches_header(header: List[str]) -> bool:
        """Riconosce la firma del report senza dipendere dal nome del file."""
        return (
            len(header) >= 2
            and header[0].strip().casefold() == "sample"
            and any(re.search(r"\s+Results$", cell.strip(), re.IGNORECASE) for cell in header[1:])
        )

    def can_handle(self, file_path: Path | str) -> bool:
        """Controlla la sola intestazione; il parsing verifica poi tutto il CSV."""
        try:
            content = self._read_text_file(Path(file_path))
            reader = csv.reader(io.StringIO(content, newline=""), strict=True)
            return self._matches_header(next(reader, []))
        except (OSError, csv.Error):
            return False

    def parse_batch(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None,
        allowed_labs: Optional[Set[str]] = None,
    ) -> ParsedBatch:
        """Restituisce campioni e scarti, usando i laboratori abilitati.

        Un codice ignorato non è un errore. Una riga campione con larghezza
        errata genera invece un avviso e non occupa la prima occorrenza utile.
        Errori CSV e intestazioni duplicate sollevano ValueError sull'intero file.
        """
        path = Path(file_path)
        reader = csv.reader(io.StringIO(self._read_text_file(path), newline=""), strict=True)
        batch = ParsedBatch()
        seen: Set[str] = set()
        trans_map = transcode_map or {}
        try:
            header = next(reader, [])
            if not self._matches_header(header):
                raise ValueError("Intestazione Agilent non valida: attesi Sample e colonne esame Results")
            names = [self._exam_name(cell) for cell in header[1:]]
            # Dopo la pulizia due colonne non devono finire sullo stesso esame.
            canonical_names = [name.casefold() for name in names]
            if any(not name or name.casefold() == "results" for name in names):
                raise ValueError("Intestazione Agilent con nome esame vuoto")
            if len(set(canonical_names)) != len(names):
                raise ValueError("Intestazione Agilent con nomi esame duplicati")
            if next(reader, None) is None:
                raise ValueError("Seconda riga Agilent mancante")

            while True:
                line_number = reader.line_num + 1
                row = next(reader, None)
                if row is None:
                    break
                if not row or not any(cell.strip() for cell in row):
                    continue
                valid, code, _ = validate_sample_code(row[0], allowed_labs)
                if not valid or code is None:
                    continue
                if len(row) != len(header):
                    batch.warnings.append(
                        f"Riga {line_number} scartata: {len(row)} colonne invece di {len(header)}"
                    )
                    continue
                if code.raw_code in seen:
                    continue

                results: List[ParsedResult] = []
                for name, raw in zip(names, row[1:]):
                    raw = raw.strip()
                    numeric, formatted = self._normalize_value(raw)
                    # NaN e Infinity non rappresentano concentrazioni numeriche:
                    # applica anche a questi la conversione concordata a zero.
                    if not math.isfinite(numeric):
                        numeric, formatted = 0.0, "0"
                    lis_code = trans_map.get(name)
                    results.append(ParsedResult(
                        param_name=name, raw_value=raw, numeric_value=numeric,
                        formatted_value=formatted, lis_exam_code=lis_code,
                        is_mapped=bool(lis_code),
                    ))
                batch.samples.append(ParsedSample(
                    sample_code=code.raw_code, source_filename=path.name,
                    results=results, instrument_name=self.name,
                ))
                seen.add(code.raw_code)
        except csv.Error as exc:
            raise ValueError(f"CSV Agilent illeggibile alla riga {reader.line_num}: {exc}") from exc

        # Se tutti i campioni sono irregolari occorre correggere il file; un
        # report valido di soli controlli può invece essere archiviato normalmente.
        batch.archive_if_empty = not batch.warnings
        return batch

    def parse_samples(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None,
    ) -> List[ParsedSample]:
        """Compatibilità lista campioni, con i prefissi laboratorio predefiniti."""
        return self.parse_batch(file_path, transcode_map).samples

    def parse_file(
        self,
        file_path: Path | str,
        transcode_map: Optional[Dict[str, str]] = None,
    ) -> ParsedSample:
        """Restituisce il primo campione; segnala l'assenza senza inventare codici."""
        samples = self.parse_samples(file_path, transcode_map)
        if not samples:
            raise ValueError("Nessun campione valido nel file Agilent")
        return samples[0]


# Registro dei driver disponibili
AVAILABLE_DRIVERS: List[Type[BaseInstrumentDriver]] = [
    DionexICDriver,
    MettlerToledoDriver,
    Agilent5977CDriver,
    SpectrophotometerDriver,
]


def get_available_driver_names() -> List[str]:
    """Restituisce l'elenco dei nomi di tutti i driver registrati nel sistema."""
    return [cls.name for cls in AVAILABLE_DRIVERS]


def get_driver_by_name(name: str) -> Optional[BaseInstrumentDriver]:
    """Restituisce un'istanza del driver in base al nome registrato."""
    for driver_cls in AVAILABLE_DRIVERS:
        if driver_cls.name.strip().lower() == name.strip().lower():
            return driver_cls()
    return None


def get_driver(
    file_path: Path | str,
    preferred_driver_name: Optional[str] = None
) -> BaseInstrumentDriver:
    """Ritorna l'istanza del driver idoneo per il file passato.

    Se viene fornito preferred_driver_name (driver di default configurato dall'admin),
    viene verificato prioritariamente. In alternativa controlla tutti i driver registrati.
    """
    path = Path(file_path)

    # 1. Se è specificato un driver preferito ed è in grado di gestire il file, usalo
    if preferred_driver_name:
        preferred = get_driver_by_name(preferred_driver_name)
        if preferred and preferred.can_handle(path):
            return preferred

    # 2. Controllo automatico tra tutti i driver registrati
    for driver_cls in AVAILABLE_DRIVERS:
        driver_instance = driver_cls()
        if driver_instance.can_handle(path):
            return driver_instance

    # 3. Fallback sul driver preferito se esistente, altrimenti sul primo driver registrato
    if preferred_driver_name:
        preferred = get_driver_by_name(preferred_driver_name)
        if preferred:
            return preferred

    return AVAILABLE_DRIVERS[0]()


def parse_instrument_file(
    file_path: Path | str,
    transcode_map: Optional[Dict[str, str]] = None,
    driver_name: Optional[str] = None
) -> ParsedSample:
    """Funzione di comodità per analizzare un file di strumento con il driver appropriato (restituisce un campione)."""
    driver = get_driver(file_path, preferred_driver_name=driver_name)
    return driver.parse_file(file_path, transcode_map)


def parse_instrument_samples(
    file_path: Path | str,
    transcode_map: Optional[Dict[str, str]] = None,
    driver_name: Optional[str] = None
) -> List[ParsedSample]:
    """Funzione di comodità per analizzare un file ed estrarre tutti i campioni presenti (supporto multi-campione)."""
    driver = get_driver(file_path, preferred_driver_name=driver_name)
    return driver.parse_samples(file_path, transcode_map)

