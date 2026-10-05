# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Dialogo Modale per la Guida e il Manuale d'Uso dell'Applicazione."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import customtkinter as ctk

from src.gui.theme import (
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_SECONDARY,
    COLOR_SECONDARY_HOVER,
    COLOR_WARNING,
    FONT_FAMILY,
    FONT_MONO,
    FONT_NORMAL,
    FONT_SECTION,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)


class HelpDialog(ctk.CTkToplevel):
    """Finestra di consultazione del Manuale d'Uso e Guida Rapida.

    Fornisce accesso completo alla documentazione operativa del software
    a tutti gli utenti (Operatori e Amministratori).
    Include un indice interattivo (TOC) navigabile con un clic e una barra
    di ricerca testuale con evidenziazione in tempo reale dei risultati.
    """

    def __init__(self, parent: ctk.CTk, manual_path: Optional[Path] = None):
        """Inizializza la maschera della Guida.

        Args:
            parent: Finestra genitore.
            manual_path: Percorso opzionale al file markdown del manuale.
        """
        super().__init__(parent)

        self.title("📖 Manuale d'Uso & Guida Rapida — Strumenti ➔ LIS")
        self.geometry("1060x720")
        self.minsize(850, 550)

        # Tracciamento posizioni capitoli nel testo (chiave: titolo, valore: indice tk es. "42.0")
        self._chapter_indices: Dict[str, str] = {}
        self._search_matches: List[str] = []
        self._current_match_idx: int = -1

        # Rilevamento percorso manuale
        self.manual_path = self._resolve_manual_path(manual_path)

        # Costruzione dell'interfaccia
        self._build_ui()

        # Carica e visualizza il testo
        self._load_and_render_manual()

        # Centra la finestra rispetto al genitore e imposta il focus
        self.after(50, self._setup_window)

    def _resolve_manual_path(self, custom_path: Optional[Path]) -> Path:
        """Determina il percorso del file manuale.md."""
        if custom_path and custom_path.exists():
            return custom_path

        # Percorsi candidati
        root_dir = Path(__file__).resolve().parent.parent.parent
        candidates = [
            root_dir / "manuale.md",
            Path("manuale.md").resolve(),
            root_dir / "MANUALE.md",
            Path("MANUALE.md").resolve(),
        ]
        for p in candidates:
            if p.exists():
                return p

        # Default al percorso standard nella root di progetto
        return root_dir / "manuale.md"

    def _setup_window(self) -> None:
        """Porta la finestra in primo piano senza bloccare forzatamente."""
        self.lift()
        self.focus_force()

    # =========================================================================
    # COSTRUZIONE UI
    # =========================================================================
    def _build_ui(self) -> None:
        """Costruisce i componenti grafici della finestra."""
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # 1. Header superiore
        self._build_header()

        # 2. Corpo principale (due colonne: Indice a sinistra, Contenuto a destra)
        body = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=0)  # Sidebar larghezza fissa
        body.grid_columnconfigure(1, weight=1)  # Viewer espandibile

        # 2a. Sidebar Indice Capitoli
        self._build_sidebar(body)

        # 2b. Visualizzatore Contenuto
        self._build_content_viewer(body)

        # 3. Footer inferiore con tasto chiusura
        self._build_footer()

    def _build_header(self) -> None:
        """Crea l'intestazione con titolo e barra di ricerca."""
        header = ctk.CTkFrame(self, height=65, corner_radius=8)
        header.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        header.grid_propagate(False)

        # Titolo e sottotitolo
        frame_title = ctk.CTkFrame(header, fg_color="transparent")
        frame_title.pack(side="left", padx=15, pady=8)

        lbl_title = ctk.CTkLabel(
            frame_title,
            text="📖 Guida Rapida & Manuale d'Uso",
            font=FONT_TITLE,
            anchor="w"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = ctk.CTkLabel(
            frame_title,
            text="Istruzioni operative per l'acquisizione, selezione ed esportazione dei campioni",
            font=FONT_SMALL,
            text_color="gray",
            anchor="w"
        )
        lbl_sub.pack(anchor="w")

        # Barra di Ricerca Rapida
        frame_search = ctk.CTkFrame(header, fg_color="transparent")
        frame_search.pack(side="right", padx=15, pady=12)

        self.entry_search = ctk.CTkEntry(
            frame_search,
            placeholder_text="🔍 Cerca nel manuale...",
            width=220,
            height=32,
            font=FONT_NORMAL
        )
        self.entry_search.pack(side="left", padx=(0, 6))
        self.entry_search.bind("<Return>", lambda e: self._on_search())
        self.entry_search.bind("<KeyRelease>", self._on_search_keyrelease)

        btn_search = ctk.CTkButton(
            frame_search,
            text="Cerca",
            width=65,
            height=32,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            font=FONT_SMALL,
            command=self._on_search
        )
        btn_search.pack(side="left", padx=2)

        btn_clear = ctk.CTkButton(
            frame_search,
            text="✕",
            width=32,
            height=32,
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SECONDARY_HOVER,
            font=FONT_SMALL,
            command=self._on_clear_search
        )
        btn_clear.pack(side="left", padx=2)

        self.lbl_search_status = ctk.CTkLabel(
            frame_search,
            text="",
            font=FONT_SMALL,
            text_color="gray"
        )
        self.lbl_search_status.pack(side="left", padx=(6, 0))

    def _build_sidebar(self, parent: ctk.CTkFrame) -> None:
        """Crea la colonna sinistra con l'indice dei capitoli (TOC)."""
        sidebar = ctk.CTkFrame(parent, width=280, corner_radius=8)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        sidebar.grid_propagate(False)

        # Intestazione sidebar
        lbl_toc = ctk.CTkLabel(
            sidebar,
            text="📑 INDICE CAPITOLI",
            font=FONT_SECTION,
            anchor="w"
        )
        lbl_toc.pack(fill="x", padx=12, pady=(12, 6))

        # Frame scorrevole con l'elenco dei pulsanti capitolo
        self.frame_toc_buttons = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.frame_toc_buttons.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_content_viewer(self, parent: ctk.CTkFrame) -> None:
        """Crea il visualizzatore del contenuto del manuale."""
        content_frame = ctk.CTkFrame(parent, corner_radius=8)
        content_frame.grid(row=0, column=1, sticky="nsew")

        # Widget di testo CustomTkinter
        self.txt_content = ctk.CTkTextbox(
            content_frame,
            wrap="word",
            font=FONT_NORMAL,
            corner_radius=8
        )
        self.txt_content.pack(fill="both", expand=True, padx=8, pady=8)

        # Configurazione tag di formattazione e colori sul widget tk sottostante
        tk_text = self.txt_content._textbox
        tk_text.tag_config("title", font=(FONT_FAMILY, 16, "bold"), foreground="#1f6aa5", spacing3=6)
        tk_text.tag_config("h2", font=(FONT_FAMILY, 13, "bold"), foreground="#388bfd", spacing1=12, spacing3=4)
        tk_text.tag_config("h3", font=(FONT_FAMILY, 11, "bold"), foreground="#79c0ff", spacing1=8, spacing3=2)
        tk_text.tag_config("code", font=FONT_MONO, background="#161b22", foreground="#7ee787")
        tk_text.tag_config("bullet", lmargin1=15, lmargin2=25)
        tk_text.tag_config("search_match", background="#d29922", foreground="#000000")
        tk_text.tag_config("active_match", background="#f0883e", foreground="#000000")

    def _build_footer(self) -> None:
        """Crea la barra inferiore con percorso del file e tasto Chiudi."""
        footer = ctk.CTkFrame(self, height=45, corner_radius=8)
        footer.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 12))
        footer.grid_propagate(False)

        lbl_path = ctk.CTkLabel(
            footer,
            text=f"Sorgente: {self.manual_path.name}",
            font=FONT_SMALL,
            text_color="gray"
        )
        lbl_path.pack(side="left", padx=15)

        btn_close = ctk.CTkButton(
            footer,
            text="Chiudi",
            width=90,
            height=30,
            fg_color=COLOR_SECONDARY,
            hover_color=COLOR_SECONDARY_HOVER,
            command=self.destroy
        )
        btn_close.pack(side="right", padx=15)

    # =========================================================================
    # CARICAMENTO E RENDERING DEL MANUALE
    # =========================================================================
    def _load_and_render_manual(self) -> None:
        """Carica il testo da manuale.md e lo formatta nel viewer."""
        raw_text = self._read_manual_text()
        self._render_text(raw_text)

    def _read_manual_text(self) -> str:
        """Legge il testo da file con fallback integrato in caso di errore."""
        if self.manual_path.exists():
            try:
                return self.manual_path.read_text(encoding="utf-8")
            except Exception as e:
                return (
                    f"# Manuale d'Uso — Strumenti ➔ LIS\n\n"
                    f"⚠️ Errore durante la lettura del file: {e}\n\n"
                    f"Percorso verificato: {self.manual_path}\n"
                )
        return (
            "# Manuale d'Uso — Strumenti ➔ LIS\n\n"
            "⚠️ File 'manuale.md' non trovato nella cartella del programma.\n\n"
            "Verificare che il file sia presente nella directory principale del software."
        )

    def _render_text(self, text: str) -> None:
        """Analizza il markdown riga per riga, popola il viewer e genera i pulsanti dell'indice."""
        self.txt_content.configure(state="normal")
        self.txt_content.delete("1.0", "end")
        self._chapter_indices.clear()

        # Pulizia pulsanti indice precedenti
        for child in self.frame_toc_buttons.winfo_children():
            child.destroy()

        lines = text.splitlines()
        tk_text = self.txt_content._textbox

        for line in lines:
            # Titolo Principale H1 (# ...)
            if line.startswith("# "):
                title = line[2:].strip()
                idx_start = tk_text.index("insert")
                tk_text.insert("end", f"{title}\n", "title")

            # Capitolo H2 (## ...)
            elif line.startswith("## "):
                ch_title = line[3:].strip()
                idx_start = tk_text.index("insert")
                tk_text.insert("end", f"\n{ch_title}\n", "h2")
                self._chapter_indices[ch_title] = idx_start

                # Aggiunge pulsante nell'indice a sinistra (escludendo 'Indice del Manuale')
                if not ch_title.lower().startswith("indice"):
                    self._create_toc_button(ch_title, idx_start)

            # Sottosezione H3 (### ...)
            elif line.startswith("### "):
                sub_title = line[4:].strip()
                tk_text.insert("end", f"\n{sub_title}\n", "h3")

            # Separatore orizzontale (---)
            elif line.strip() == "---":
                tk_text.insert("end", f"{'─' * 60}\n")

            # Elenco puntato (- ... o * ...)
            elif line.startswith(("- ", "* ")):
                bullet_content = line[2:].strip()
                # Rimozione eventuale grassetto markdown semplice **testo**
                cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", bullet_content)
                tk_text.insert("end", f" • {cleaned}\n", "bullet")

            # Righe normali o tabelle
            else:
                cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
                cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)
                tk_text.insert("end", f"{cleaned}\n")

        # Rendiamo il testo di sola lettura per evitare modifiche accidentali
        self.txt_content.configure(state="disabled")

    def _create_toc_button(self, title: str, text_index: str) -> None:
        """Crea un pulsante per il capitolo nell'indice laterale."""
        # Pulisci il titolo per renderlo compatto nel pulsante
        display_title = title
        if len(display_title) > 32:
            display_title = display_title[:30] + "..."

        btn = ctk.CTkButton(
            self.frame_toc_buttons,
            text=display_title,
            anchor="w",
            height=30,
            font=FONT_SMALL,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=COLOR_PRIMARY_HOVER,
            command=lambda idx=text_index: self._jump_to_chapter(idx)
        )
        btn.pack(fill="x", pady=2)

    def _jump_to_chapter(self, text_index: str) -> None:
        """Scorre il visualizzatore direttamente all'indice del capitolo selezionato."""
        tk_text = self.txt_content._textbox
        tk_text.see(text_index)

        # Breve evidenziazione visiva della riga
        try:
            line_end = f"{text_index.split('.')[0]}.end"
            tk_text.tag_remove("active_match", "1.0", "end")
            tk_text.tag_add("active_match", text_index, line_end)
            self.after(1500, lambda: tk_text.tag_remove("active_match", "1.0", "end"))
        except Exception:
            pass

    # =========================================================================
    # RICERCA TESTUALE
    # =========================================================================
    def _on_search_keyrelease(self, event) -> None:
        """Se il testo di ricerca viene cancellato, pulisce le evidenziazioni."""
        if not self.entry_search.get().strip():
            self._on_clear_search()

    def _on_search(self) -> None:
        """Cerca il testo specificato nel manuale ed evidenzia tutte le occorrenze."""
        query = self.entry_search.get().strip()
        tk_text = self.txt_content._textbox

        # Rimuovi evidenziazioni precedenti
        tk_text.tag_remove("search_match", "1.0", "end")
        tk_text.tag_remove("active_match", "1.0", "end")
        self._search_matches.clear()
        self._current_match_idx = -1

        if not query:
            self.lbl_search_status.configure(text="")
            return

        # Ricerca case-insensitive
        start_idx = "1.0"
        while True:
            pos = tk_text.search(query, start_idx, stopindex="end", nocase=True)
            if not pos:
                break
            end_pos = f"{pos}+{len(query)}c"
            tk_text.tag_add("search_match", pos, end_pos)
            self._search_matches.append(pos)
            start_idx = end_pos

        count = len(self._search_matches)
        if count == 0:
            self.lbl_search_status.configure(text="Nessun risultato", text_color=COLOR_WARNING)
        else:
            self.lbl_search_status.configure(text=f"{count} trovati", text_color=COLOR_PRIMARY)
            # Salta alla prima occorrenza
            self._current_match_idx = 0
            first_pos = self._search_matches[0]
            tk_text.see(first_pos)
            end_first = f"{first_pos}+{len(query)}c"
            tk_text.tag_add("active_match", first_pos, end_first)

    def _on_clear_search(self) -> None:
        """Pulisce il campo di ricerca e le evidenziazioni nel testo."""
        self.entry_search.delete(0, "end")
        self.lbl_search_status.configure(text="")
        tk_text = self.txt_content._textbox
        tk_text.tag_remove("search_match", "1.0", "end")
        tk_text.tag_remove("active_match", "1.0", "end")
        self._search_matches.clear()
        self._current_match_idx = -1
