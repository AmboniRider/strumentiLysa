# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modulo di Validazione e Parsing del Codice Campione.

Questo modulo implementa la logica di validazione posizionale per il codice
campione a 18 caratteri secondo le specifiche del LIS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Set

DEFAULT_ALLOWED_LABS: Set[str] = {"BG", "MI", "BS", "RL", "VP", "MN", "MB"}


@dataclass
class ValidatedSampleCode:
    """Rappresenta le componenti estratte e validate da un codice campione a 18 caratteri."""
    raw_code: str
    lab_code: str
    year_2digit: int
    year_4digit: int
    acceptance: str
    conferment: int
    sample_number: int

    @property
    def conferment_str(self) -> str:
        """Ritorna il conferimento senza zeri iniziali."""
        return str(self.conferment)

    @property
    def sample_number_str(self) -> str:
        """Ritorna il numero campione senza zeri iniziali."""
        return str(self.sample_number)


def validate_sample_code(
    code: str,
    allowed_labs: Optional[Set[str]] = None
) -> tuple[bool, Optional[ValidatedSampleCode], str]:
    """Valida un codice campione a 18 caratteri ed estrae le componenti strutturate.

    Args:
        code: Stringa del codice campione.
        allowed_labs: Insieme dei prefissi di laboratorio ammessi (default: BG, MI, BS, RL, VP, MN, MB).

    Returns:
        Tupla (is_valid: bool, data: Optional[ValidatedSampleCode], error_message: str)
    """
    clean_code = code.strip().upper()
    valid_labs = allowed_labs if allowed_labs is not None else DEFAULT_ALLOWED_LABS

    if len(clean_code) != 18:
        return False, None, f"Lunghezza codice non valida ({len(clean_code)} caratteri invece di 18): '{clean_code}'"

    lab = clean_code[0:2]
    if lab not in valid_labs:
        return False, None, f"Codice laboratorio '{lab}' non riconosciuto tra quelli abilitati ({', '.join(sorted(valid_labs))})"

    # Controllo che i restanti 16 caratteri siano numerici
    digits_part = clean_code[2:]
    if not digits_part.isdigit():
        return False, None, f"La porzione posizionale 3-18 deve contenere solo cifre numeriche: '{digits_part}'"

    # Pos 3-4: Anno
    year_2d = int(clean_code[2:4])
    # Conversione anno a 4 cifre (2000-2099)
    year_4d = 2000 + year_2d

    # Pos 5-6: Filler costante '00'
    filler = clean_code[4:6]
    if filler != "00":
        return False, None, f"I caratteri in posizione 5-6 devono essere '00' (trovato: '{filler}')"

    # Pos 7-11: Accettazione (5 cifre)
    acceptance = clean_code[6:11]

    # Pos 12-14: Conferimento (3 cifre)
    conferment = int(clean_code[11:14])

    # Pos 15-18: Campione (4 cifre)
    sample_num = int(clean_code[14:18])

    data = ValidatedSampleCode(
        raw_code=clean_code,
        lab_code=lab,
        year_2digit=year_2d,
        year_4digit=year_4d,
        acceptance=acceptance,
        conferment=conferment,
        sample_number=sample_num,
    )
    return True, data, ""
