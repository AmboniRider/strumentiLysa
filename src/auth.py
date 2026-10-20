# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Modulo di Autenticazione e Sicurezza Utenti.

Gestisce la sicurezza delle credenziali tramite hashing SHA-256 e salt crittografico,
la verifica dell'accesso e lo stato della sessione attiva.
"""

from __future__ import annotations

import hashlib
import secrets
from typing import Optional

from src.models import UserRecord


def generate_salt() -> str:
    """Genera un salt crittografico casuale a 16 byte (32 caratteri esadecimali)."""
    return secrets.token_hex(16)


def hash_password(password: str, salt: str) -> str:
    """Calcola l'hash SHA-256 della password concatenata con il salt."""
    salted = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifica se la password corrisponde all'hash memorizzato."""
    computed = hash_password(password, salt)
    return secrets.compare_digest(computed, stored_hash)


class SessionManager:
    """Gestore singleton dello stato di autenticazione corrente dell'applicazione."""

    _current_user: Optional[UserRecord] = None

    @classmethod
    def set_user(cls, user: UserRecord) -> None:
        cls._current_user = user

    @classmethod
    def get_user(cls) -> Optional[UserRecord]:
        return cls._current_user

    @classmethod
    def is_logged_in(cls) -> bool:
        return cls._current_user is not None

    @classmethod
    def is_admin(cls) -> bool:
        return cls._current_user is not None and cls._current_user.role.upper() == "ADMIN"

    @classmethod
    def logout(cls) -> None:
        cls._current_user = None
