# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Finestra Principale dell'Applicazione CustomTkinter.

Gestisce la navigazione tra schermata di login e dashboard principale Master-Detail.
"""

from __future__ import annotations

import customtkinter as ctk
from pathlib import Path
from tkinter import TclError
import logging
from typing import Optional

from src.auth import SessionManager
from src.database import Database
from src.gui.login_view import LoginView
from src.gui.master_detail import MasterDetailView
from src.models import UserRecord


class AppWindow(ctk.CTk):
    """Finestra principale dell'interfaccia grafica."""

    def __init__(self, db: Database):
        super().__init__()
        self.set_app_icon()
        self.db = db

        self.update_app_title()
        self.geometry("1180x760")
        self.minsize(980, 640)

    def set_app_icon(self) -> None:
        """Carica l'icona del progetto per la finestra e i dialoghi figli."""
        # Il percorso assoluto permette l'avvio anche da una cartella diversa.
        icon_path = Path(__file__).resolve().parents[2] / "strumenti.ico"
        try:
            if self.tk.call("tk", "windowingsystem") == "win32":
                # CustomTkinter registra questa chiamata e non sovrascrive l'icona.
                self.iconbitmap(str(icon_path), default=str(icon_path))
            else:
                from PIL import Image, ImageTk

                # Tk su Linux/macOS richiede un'immagine invece del formato ICO.
                with Image.open(icon_path) as icon:
                    self._app_icon = ImageTk.PhotoImage(icon.copy(), master=self)
                self.iconphoto(True, self._app_icon)
        except (OSError, TclError):
            # Un asset mancante o non leggibile non deve impedire l'accesso al LIS.
            logging.getLogger(__name__).warning("Impossibile caricare l'icona %s", icon_path)

    def update_app_title(self) -> None:
        """Aggiorna il titolo della finestra principale includendo la versione corrente."""
        config = self.db.get_config()
        self.title(f"Interfaccia Strumenti di Laboratorio - LIS - Versione {config.app_version}")

        # Configurazione Tema CustomTkinter
        ctk.set_appearance_mode("System")  # Segue il tema del sistema operativo
        ctk.set_default_color_theme("blue")

        self.current_view: Optional[ctk.CTkFrame] = None

        # Mostra schermata iniziale di login
        self.show_login()

    def show_login(self) -> None:
        """Mostra la schermata di login."""
        SessionManager.logout()
        if self.current_view:
            self.current_view.destroy()

        self.current_view = LoginView(
            master=self,
            db=self.db,
            on_login_success=self.show_dashboard
        )
        self.current_view.pack(fill="both", expand=True)

    def show_dashboard(self, user: UserRecord) -> None:
        """Mostra la dashboard principale per l'utente autenticato."""
        if self.current_view:
            self.current_view.destroy()

        self.current_view = MasterDetailView(
            master=self,
            db=self.db,
            current_user=user,
            on_logout=self.show_login
        )
        self.current_view.pack(fill="both", expand=True)
