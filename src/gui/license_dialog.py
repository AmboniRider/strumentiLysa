# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Consultazione offline di attribuzione, disclaimer e licenza integrale."""

from __future__ import annotations

from pathlib import Path
import re
import webbrowser

import customtkinter as ctk

from src import __author__

REPOSITORY_URL = "https://github.com/AmboniRider/strumentiLysa"


def read_legal_file(root: Path, filename: str) -> str:
    """Legge un documento distribuito; un file mancante non blocca l'applicazione."""
    try:
        return (root / filename).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return f"Impossibile caricare {filename}. Ripristinare il file nella cartella del programma."


class LicenseDialog(ctk.CTkToplevel):
    """Finestra pubblica senza vincoli di ruolo, con testi selezionabili e in sola lettura."""

    def __init__(self, parent: ctk.CTk, root_dir: Path | None = None):
        """Mostra i documenti locali della root, indipendentemente dalla directory corrente."""
        super().__init__(parent)
        self.title("Licenza e responsabilità")
        self.geometry("920x700")
        self.minsize(720, 500)
        self.transient(parent)
        root = root_dir if root_dir is not None else Path(__file__).resolve().parents[2]
        ctk.CTkLabel(self, text="Licenza e responsabilità", font=("Segoe UI", 21, "bold")).pack(pady=(15, 5))
        ctk.CTkLabel(self, text=f"Autore: {__author__}  |  AGPL-3.0-or-later").pack(pady=(0, 8))
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=18, pady=5)
        overview = self.tabs.add("Licenza e responsabilità")
        full_license = self.tabs.add("Testo integrale AGPLv3")
        legal = read_legal_file(root, "LEGAL.md")
        # Rimuoviamo soltanto la sintassi Markdown dall'avviso. Il testo LICENSE
        # viene invece mostrato integralmente, senza alcuna trasformazione.
        legal = re.sub(r"^#{1,6} ", "", legal, flags=re.MULTILINE).replace("**", "")
        self.disclaimer_text = self._text(overview, legal)
        self.license_text = self._text(full_license, read_legal_file(root, "LICENSE"))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=18, pady=(8, 15))
        self.repository_button = ctk.CTkButton(actions, text=REPOSITORY_URL,
                                              command=lambda: webbrowser.open(REPOSITORY_URL))
        self.repository_button.pack(side="left")
        ctk.CTkButton(actions, text="Chiudi", width=90, command=self.destroy).pack(side="right")

    @staticmethod
    def _text(parent: ctk.CTkFrame, content: str) -> ctk.CTkTextbox:
        """Mantiene scorrimento e copia del testo senza consentire modifiche."""
        viewer = ctk.CTkTextbox(parent, wrap="word", font=("Segoe UI", 13))
        viewer.pack(fill="both", expand=True)
        viewer.insert("1.0", content)
        viewer.configure(state="disabled")
        return viewer
