# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Vista di Autenticazione (Login) CustomTkinter."""

from __future__ import annotations

import customtkinter as ctk
from typing import Callable, Optional

from src.auth import SessionManager, verify_password
from src.database import Database
from src.gui.theme import (
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    FONT_NORMAL,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)
from src.models import UserRecord


class LoginView(ctk.CTkFrame):
    """Schermata di Login dell'applicazione."""

    def __init__(
        self,
        master: ctk.CTk,
        db: Database,
        on_login_success: Callable[[UserRecord], None],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.db = db
        self.on_login_success = on_login_success

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Centra la card di login
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(2, weight=1)

        # Card centrale
        card = ctk.CTkFrame(self, corner_radius=12, width=420, height=480)
        card.grid(row=1, column=1, sticky="nsew", padx=20, pady=20)
        card.grid_propagate(False)

        # Titolo e Icona
        lbl_icon = ctk.CTkLabel(card, text="🔬", font=("Segoe UI Emoji", 40))
        lbl_icon.pack(pady=(25, 5))

        lbl_title = ctk.CTkLabel(
            card,
            text="STRUMENTI ➔ LIS",
            font=FONT_TITLE
        )
        lbl_title.pack(pady=(0, 2))

        lbl_subtitle = ctk.CTkLabel(
            card,
            text="Interfaccia Strumenti di Laboratorio",
            font=FONT_SMALL,
            text_color="gray"
        )
        lbl_subtitle.pack(pady=(0, 20))

        # Form Inputs
        form_frame = ctk.CTkFrame(card, fg_color="transparent")
        form_frame.pack(fill="x", padx=35)

        # Username
        lbl_user = ctk.CTkLabel(form_frame, text="Nome Utente", font=FONT_NORMAL, anchor="w")
        lbl_user.pack(fill="x", pady=(5, 2))
        self.entry_user = ctk.CTkEntry(
            form_frame,
            placeholder_text="es. admin",
            font=FONT_NORMAL,
            height=38
        )
        self.entry_user.pack(fill="x", pady=(0, 10))
        self.entry_user.bind("<Return>", lambda e: self.entry_pwd.focus_set())

        # Password
        lbl_pwd = ctk.CTkLabel(form_frame, text="Password", font=FONT_NORMAL, anchor="w")
        lbl_pwd.pack(fill="x", pady=(5, 2))
        self.entry_pwd = ctk.CTkEntry(
            form_frame,
            placeholder_text="Password",
            show="•",
            font=FONT_NORMAL,
            height=38
        )
        self.entry_pwd.pack(fill="x", pady=(0, 10))
        self.entry_pwd.bind("<Return>", lambda e: self._handle_login())

        # Etichetta Errore
        self.lbl_error = ctk.CTkLabel(
            form_frame,
            text="",
            font=FONT_SMALL,
            text_color=COLOR_DANGER
        )
        self.lbl_error.pack(pady=(0, 10))

        # Pulsante Accedi
        self.btn_login = ctk.CTkButton(
            form_frame,
            text="Accedi al Sistema",
            font=FONT_SUBTITLE,
            height=42,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._handle_login
        )
        self.btn_login.pack(fill="x", pady=(5, 10))

        # Info credenziali di default
        lbl_hint = ctk.CTkLabel(
            card,
            text="Credenziali predefinite: admin / admin",
            font=("Segoe UI", 9),
            text_color="gray"
        )
        lbl_hint.pack(side="bottom", pady=(0, 15))

        # Focus iniziale
        self.entry_user.focus_set()

    def _handle_login(self) -> None:
        username = self.entry_user.get().strip()
        password = self.entry_pwd.get().strip()

        if not username or not password:
            self.lbl_error.configure(text="Inserisci nome utente e password")
            return

        user = self.db.get_user_by_username(username)
        if not user or not verify_password(password, user.password_hash, user.salt):
            self.lbl_error.configure(text="Credenziali non corrette")
            self.entry_pwd.delete(0, "end")
            self.entry_pwd.focus_set()
            return

        # Login riuscito
        self.db.update_user_last_login(user.id) # type: ignore
        SessionManager.set_user(user)
        self.db.log_action(user.id, user.username, "USER_LOGIN", "Accesso eseguito con successo")
        self.on_login_success(user)
