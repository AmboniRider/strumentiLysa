# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Dialogo Modale per il Cambio Password Utente."""

from __future__ import annotations

import customtkinter as ctk
from typing import Optional

from src.auth import verify_password
from src.database import Database
from src.gui.theme import (
    COLOR_DANGER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS,
    FONT_NORMAL,
    FONT_SECTION,
    FONT_SMALL,
)
from src.models import UserRecord


class PasswordDialog(ctk.CTkToplevel):
    """Finestra di dialogo per la modifica della password."""

    def __init__(self, parent: ctk.CTk, db: Database, user: UserRecord):
        super().__init__(parent)
        self.db = db
        self.user = user

        self.title("Modifica Password")
        self.geometry("380x360")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

    def _create_widgets(self) -> None:
        frame = ctk.CTkFrame(self, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        lbl_title = ctk.CTkLabel(
            frame,
            text=f"Cambio Password ({self.user.username})",
            font=FONT_SECTION
        )
        lbl_title.pack(pady=(15, 10))

        # Vecchia Password
        ctk.CTkLabel(frame, text="Password Attuale", font=FONT_SMALL, anchor="w").pack(fill="x", padx=20, pady=(5, 2))
        self.entry_old_pwd = ctk.CTkEntry(frame, show="•", font=FONT_NORMAL)
        self.entry_old_pwd.pack(fill="x", padx=20, pady=(0, 10))

        # Nuova Password
        ctk.CTkLabel(frame, text="Nuova Password", font=FONT_SMALL, anchor="w").pack(fill="x", padx=20, pady=(5, 2))
        self.entry_new_pwd = ctk.CTkEntry(frame, show="•", font=FONT_NORMAL)
        self.entry_new_pwd.pack(fill="x", padx=20, pady=(0, 10))

        # Conferma Nuova Password
        ctk.CTkLabel(frame, text="Conferma Nuova Password", font=FONT_SMALL, anchor="w").pack(fill="x", padx=20, pady=(5, 2))
        self.entry_confirm_pwd = ctk.CTkEntry(frame, show="•", font=FONT_NORMAL)
        self.entry_confirm_pwd.pack(fill="x", padx=20, pady=(0, 10))

        self.lbl_msg = ctk.CTkLabel(frame, text="", font=FONT_SMALL)
        self.lbl_msg.pack(pady=(0, 10))

        # Pulsanti
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 15))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text="Annulla",
            fg_color="gray",
            hover_color="#555555",
            width=100,
            command=self.destroy
        )
        btn_cancel.pack(side="left", padx=(0, 10))

        btn_save = ctk.CTkButton(
            btn_frame,
            text="Salva Password",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._save_password
        )
        btn_save.pack(side="right", fill="x", expand=True)

    def _save_password(self) -> None:
        old_p = self.entry_old_pwd.get()
        new_p = self.entry_new_pwd.get()
        conf_p = self.entry_confirm_pwd.get()

        if not old_p or not new_p or not conf_p:
            self.lbl_msg.configure(text="Compila tutti i campi", text_color=COLOR_DANGER)
            return

        if not verify_password(old_p, self.user.password_hash, self.user.salt):
            self.lbl_msg.configure(text="Password attuale errata", text_color=COLOR_DANGER)
            return

        if new_p != conf_p:
            self.lbl_msg.configure(text="Le nuove password non coincidono", text_color=COLOR_DANGER)
            return

        if len(new_p) < 3:
            self.lbl_msg.configure(text="Password troppo breve (min. 3 caratteri)", text_color=COLOR_DANGER)
            return

        ok, msg = self.db.update_user_password(self.user.id, new_p) # type: ignore
        if ok:
            # Aggiorna anche l'istanza user in memoria
            updated_user = self.db.get_user_by_username(self.user.username)
            if updated_user:
                self.user.password_hash = updated_user.password_hash
                self.user.salt = updated_user.salt
            self.lbl_msg.configure(text="Password aggiornata!", text_color=COLOR_SUCCESS)
            self.after(1000, self.destroy)
        else:
            self.lbl_msg.configure(text=msg, text_color=COLOR_DANGER)
