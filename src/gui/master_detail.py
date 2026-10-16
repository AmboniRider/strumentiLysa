# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Vista Principale Master-Detail dell'Applicazione CustomTkinter."""

from __future__ import annotations

import customtkinter as ctk
from datetime import datetime
from tkinter import font as tkfont, messagebox, ttk
from typing import Callable, Dict, List, Optional, Set

from src.auth import SessionManager
from src.config import AppConfig
from src.database import Database
from src.exporter import LISExporter
from src.gui.help_dialog import HelpDialog
from src.gui.password_dialog import PasswordDialog
from src.gui.settings_dialog import SettingsDialog
from src.gui.theme import (
    COLOR_CARD_DARK,
    COLOR_CARD_LIGHT,
    COLOR_DANGER,
    COLOR_DANGER_HOVER,
    COLOR_EXAM_SELECTED_BG,
    COLOR_EXAM_SELECTED_TEXT,
    COLOR_EXAM_SENT_BG,
    COLOR_EXAM_SENT_TEXT,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_SECONDARY,
    COLOR_SUCCESS,
    COLOR_SUCCESS_HOVER,
    COLOR_WARNING,
    FONT_MONO,
    FONT_MONO_BOLD,
    FONT_NORMAL,
    FONT_SECTION,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)
from src.importer_service import ImporterService
from src.models import ParsedResult, SampleFilter, SampleRecord, UserRecord


class MasterDetailView(ctk.CTkFrame):
    """Dashboard operativa Master-Detail per la gestione dei campioni e parametri."""

    def __init__(
        self,
        master: ctk.CTk,
        db: Database,
        current_user: UserRecord,
        on_logout: Callable[[], None],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.db = db
        self.current_user = current_user
        self.on_logout = on_logout

        self.importer_service = ImporterService(self.db)
        self.exporter = LISExporter(self.db)

        # Set di ID campioni selezionati per l'esportazione (default: tutti quelli visualizzati)
        self.selected_sample_ids: Set[int] = set()
        # Mappatura ID campione -> Set di ID test selezionati per l'esportazione
        self.selected_tests_by_sample: Dict[int, Set[int]] = {}
        self.loaded_samples: List[SampleRecord] = []
        self.selected_sample_for_detail: Optional[SampleRecord] = None
        # Cache esclusivamente grafica dello stato LIS del dettaglio mostrato.
        self._detail_exported_ids: Set[int] = set()

        self._create_widgets()
        self._load_samples()

    def _create_widgets(self) -> None:
        # Layout principale a griglia verticale
        self.grid_rowconfigure(2, weight=3)  # Master Table
        self.grid_rowconfigure(3, weight=2)  # Detail Table
        self.grid_columnconfigure(0, weight=1)

        # 1. Header Bar
        self._build_header(row=0)

        # 2. Control & Filters Toolbar
        self._build_toolbar(row=1)

        # 3. Master Panel (Tabella Campioni)
        self._build_master_panel(row=2)

        # 4. Detail Panel (Griglia Parametri)
        self._build_detail_panel(row=3)

        # 5. Footer / Action Bar
        self._build_footer(row=4)

    # =========================================================================
    # 1. HEADER BAR
    # =========================================================================
    def _build_header(self, row: int) -> None:
        header = ctk.CTkFrame(self, height=54, corner_radius=0)
        header.grid(row=row, column=0, sticky="ew", padx=0, pady=0)
        header.grid_propagate(False)

        # Logo e Titolo con Versione Software
        config = self.db.get_config()
        self.lbl_brand = ctk.CTkLabel(
            header,
            text=f"🔬 STRUMENTI ➔ LIS v{config.app_version}",
            font=FONT_TITLE
        )
        self.lbl_brand.pack(side="left", padx=(15, 10))

        lbl_sub = ctk.CTkLabel(
            header,
            text="|  Interfaccia Acquisizione ed Esportazione Laboratorio",
            font=FONT_SMALL,
            text_color="gray"
        )
        lbl_sub.pack(side="left")

        # Sezione Utente e Azioni Rapide a Destra
        btn_logout = ctk.CTkButton(
            header,
            text="🚪 Esci",
            width=70,
            height=30,
            fg_color=COLOR_SECONDARY,
            hover_color="#444444",
            command=self.on_logout
        )
        btn_logout.pack(side="right", padx=(5, 15))

        btn_pwd = ctk.CTkButton(
            header,
            text="🔑 Password",
            width=85,
            height=30,
            fg_color=COLOR_SECONDARY,
            hover_color="#444444",
            command=self._open_password_dialog
        )
        btn_pwd.pack(side="right", padx=5)

        btn_help = ctk.CTkButton(
            header,
            text="❓ Guida",
            width=75,
            height=30,
            fg_color=COLOR_SECONDARY,
            hover_color="#444444",
            command=self._open_help_dialog
        )
        btn_help.pack(side="right", padx=5)

        if self.current_user.role.upper() == "ADMIN":
            btn_settings = ctk.CTkButton(
                header,
                text="⚙️ Impostazioni",
                width=110,
                height=30,
                fg_color=COLOR_PRIMARY,
                hover_color=COLOR_PRIMARY_HOVER,
                command=self._open_settings_dialog
            )
            btn_settings.pack(side="right", padx=5)

            btn_maint = ctk.CTkButton(
                header,
                text="🧹 Elimina Esportati",
                width=135,
                height=30,
                fg_color=COLOR_DANGER,
                hover_color=COLOR_DANGER_HOVER,
                command=self._open_maintenance_dialog
            )
            btn_maint.pack(side="right", padx=5)

        # Badge Utente
        role_color = COLOR_PRIMARY if self.current_user.role == "ADMIN" else COLOR_SUCCESS
        lbl_role = ctk.CTkLabel(
            header,
            text=f" {self.current_user.role} ",
            font=("Segoe UI", 9, "bold"),
            fg_color=role_color,
            corner_radius=4,
            text_color="white"
        )
        lbl_role.pack(side="right", padx=(5, 10))

        lbl_user = ctk.CTkLabel(
            header,
            text=f"Utente: {self.current_user.username}",
            font=FONT_NORMAL
        )
        lbl_user.pack(side="right", padx=5)

    # =========================================================================
    # 2. TOOLBAR CONTROLLI & FILTRI
    # =========================================================================
    def _build_toolbar(self, row: int) -> None:
        toolbar = ctk.CTkFrame(self, height=52, corner_radius=8)
        toolbar.grid(row=row, column=0, sticky="ew", padx=15, pady=(10, 5))

        # Pulsante Importa
        btn_import = ctk.CTkButton(
            toolbar,
            text="📥 Carica Nuovi File",
            font=FONT_SUBTITLE,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            height=36,
            command=self._handle_import_files
        )
        btn_import.pack(side="left", padx=10, pady=8)

        # Separatore visivo
        ctk.CTkLabel(toolbar, text="|", text_color="gray").pack(side="left", padx=5)

        # Ricerca Testuale
        lbl_search = ctk.CTkLabel(toolbar, text="🔍", font=FONT_NORMAL)
        lbl_search.pack(side="left", padx=(5, 2))

        self.entry_search = ctk.CTkEntry(
            toolbar,
            placeholder_text="Cerca codice, accettazione, lab...",
            width=230,
            height=34,
            font=FONT_NORMAL
        )
        self.entry_search.pack(side="left", padx=(0, 10))
        self.entry_search.bind("<KeyRelease>", lambda e: self._on_filter_changed())

        # Filtro Stato (Default: 'Da Esportare' per mostrare subito i campioni pronti per l'invio al LIS)
        ctk.CTkLabel(toolbar, text="Stato:", font=FONT_SMALL).pack(side="left", padx=(5, 2))
        self.combo_status = ctk.CTkComboBox(
            toolbar,
            values=["Da Esportare", "Esportati", "Tutti"],
            width=130,
            height=34,
            font=FONT_NORMAL,
            state="readonly",
            command=lambda v: self._on_filter_changed()
        )
        self.combo_status.set("Da Esportare")
        self.combo_status.pack(side="left", padx=(0, 10))

        # Filtro Temporale (Default Ultimo Mese)
        ctk.CTkLabel(toolbar, text="Periodo:", font=FONT_SMALL).pack(side="left", padx=(5, 2))
        self.combo_date = ctk.CTkComboBox(
            toolbar,
            values=["Ultimo Mese", "Ultimi 7 Giorni", "Ultimi 3 Mesi", "Anno Corrente", "Tutti"],
            width=140,
            height=34,
            font=FONT_NORMAL,
            state="readonly",
            command=lambda v: self._on_filter_changed()
        )
        self.combo_date.set("Ultimo Mese")
        self.combo_date.pack(side="left", padx=(0, 10))

        # Pulsante Aggiorna
        btn_refresh = ctk.CTkButton(
            toolbar,
            text="🔄 Aggiorna",
            width=90,
            height=34,
            fg_color=COLOR_SECONDARY,
            hover_color="#555555",
            command=self._load_samples
        )
        btn_refresh.pack(side="left", padx=5)

        # Checkbox Selezione Globale a Destra
        btn_sel_all = ctk.CTkButton(
            toolbar,
            text="Seleziona Tutti",
            width=110,
            height=32,
            fg_color="transparent",
            border_width=1,
            text_color=("black", "white"),
            command=self._select_all_visible
        )
        btn_sel_all.pack(side="right", padx=(5, 10))

        btn_desel_all = ctk.CTkButton(
            toolbar,
            text="Deseleziona",
            width=90,
            height=32,
            fg_color="transparent",
            border_width=1,
            text_color=("black", "white"),
            command=self._deselect_all_visible
        )
        btn_desel_all.pack(side="right", padx=5)

    # =========================================================================
    # 3. MASTER PANEL (TABELLA CAMPIONI)
    # =========================================================================
    def _build_master_panel(self, row: int) -> None:
        master_frame = ctk.CTkFrame(self, corner_radius=8)
        master_frame.grid(row=row, column=0, sticky="nsew", padx=15, pady=(5, 5))

        # Intestazione Sezione Master
        sec_header = ctk.CTkFrame(master_frame, height=32, fg_color="transparent")
        sec_header.pack(fill="x", padx=10, pady=(6, 2))
        lbl_sec = ctk.CTkLabel(sec_header, text="📋 Elenco Campioni Acquisiti", font=FONT_SECTION)
        lbl_sec.pack(side="left")

        lbl_hint = ctk.CTkLabel(
            sec_header,
            text="(Fai doppio clic o premi Spazio sulla riga per selezionare/deselezionare per l'esportazione)",
            font=FONT_SMALL,
            text_color="gray"
        )
        lbl_hint.pack(side="left", padx=10)

        # Tabella Master con ttk.Treeview
        tree_container = ctk.CTkFrame(master_frame, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("sel", "code", "lab", "year", "acc", "conf", "samp", "params", "imported", "status")
        self.tree_master = ttk.Treeview(tree_container, columns=cols, show="headings", selectmode="browse")

        self.tree_master.heading("sel", text="Export")
        self.tree_master.heading("code", text="Codice Campione (18 car.)")
        self.tree_master.heading("lab", text="Lab")
        self.tree_master.heading("year", text="Anno")
        self.tree_master.heading("acc", text="Accettazione")
        self.tree_master.heading("conf", text="Conf.")
        self.tree_master.heading("samp", text="Camp.")
        self.tree_master.heading("params", text="N. Parametri")
        self.tree_master.heading("imported", text="Data Importazione")
        self.tree_master.heading("status", text="Stato LIS")

        self.tree_master.column("sel", width=55, anchor="center")
        self.tree_master.column("code", width=190, anchor="w")
        self.tree_master.column("lab", width=50, anchor="center")
        self.tree_master.column("year", width=55, anchor="center")
        self.tree_master.column("acc", width=95, anchor="center")
        self.tree_master.column("conf", width=55, anchor="center")
        self.tree_master.column("samp", width=55, anchor="center")
        self.tree_master.column("params", width=85, anchor="center")
        self.tree_master.column("imported", width=145, anchor="center")
        self.tree_master.column("status", width=120, anchor="center")

        sb_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_master.yview)
        sb_x = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree_master.xview)
        self.tree_master.configure(yscrollcommand=sb_y.set, xscrollcommand=sb_x.set)

        self.tree_master.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")

        # Eventi di selezione e click
        self.tree_master.bind("<<TreeviewSelect>>", self._on_master_row_selected)
        self.tree_master.bind("<Double-1>", self._on_master_row_double_click)
        self.tree_master.bind("<space>", self._on_master_row_space)

    # =========================================================================
    # 4. DETAIL PANEL (GRIGLIA PARAMETRI)
    # =========================================================================
    def _build_detail_panel(self, row: int) -> None:
        detail_frame = ctk.CTkFrame(self, corner_radius=8)
        detail_frame.grid(row=row, column=0, sticky="nsew", padx=15, pady=(5, 5))

        # Intestazione Sezione Detail
        sec_header = ctk.CTkFrame(detail_frame, height=32, fg_color="transparent")
        sec_header.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_detail_title = ctk.CTkLabel(
            sec_header,
            text="🔬 Parametri e Risultati Analitici (Nessun campione selezionato)",
            font=FONT_SECTION
        )
        self.lbl_detail_title.pack(side="left")

        # Pulsanti Selezione Globale Test per il campione attivo a Destra
        self.btn_desel_tests = ctk.CTkButton(
            sec_header,
            text="Deseleziona",
            width=85,
            height=26,
            font=FONT_SMALL,
            fg_color="transparent",
            border_width=1,
            text_color=("black", "white"),
            command=self._deselect_all_tests_current_sample
        )
        self.btn_desel_tests.pack(side="right", padx=(5, 0))

        self.btn_sel_all_tests = ctk.CTkButton(
            sec_header,
            text="Seleziona Tutti",
            width=100,
            height=26,
            font=FONT_SMALL,
            fg_color="transparent",
            border_width=1,
            text_color=("black", "white"),
            command=self._select_all_tests_current_sample
        )
        self.btn_sel_all_tests.pack(side="right", padx=(5, 0))

        self.lbl_detail_legend = ctk.CTkLabel(
            detail_frame,
            text="Verde: selezionato per export · Grigio: già inviato",
            font=FONT_SMALL,
            anchor="w",
        )
        self.lbl_detail_legend.pack(fill="x", padx=10, pady=(0, 3))

        # Tabella Detail
        tree_container = ctk.CTkFrame(detail_frame, fg_color="transparent")
        tree_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("sel", "status_lis", "param", "lis_code", "substance", "raw_val", "fmt_val", "mapping")
        self.tree_detail = ttk.Treeview(
            tree_container, columns=cols, show="headings", selectmode="browse",
            style="ExamDetail.Treeview",
        )
        self._configure_detail_row_styles()

        self.tree_detail.heading("sel", text="Export")
        self.tree_detail.heading("status_lis", text="Stato LIS")
        self.tree_detail.heading("param", text="Parametro Strumento")
        self.tree_detail.heading("lis_code", text="Codice Esame LIS")
        self.tree_detail.heading("substance", text="Codice sostanza LIS")
        self.tree_detail.heading("raw_val", text="Valore Originale")
        self.tree_detail.heading("fmt_val", text="Valore Esportato LIS")
        self.tree_detail.heading("mapping", text="Stato Mappatura")

        self.tree_detail.column("sel", width=55, anchor="center")
        self.tree_detail.column("status_lis", width=105, anchor="center")
        self.tree_detail.column("param", width=200, anchor="w")
        self.tree_detail.column("lis_code", width=130, anchor="center")
        self.tree_detail.column("substance", width=130, anchor="center")
        self.tree_detail.column("raw_val", width=130, anchor="center")
        self.tree_detail.column("fmt_val", width=130, anchor="center")
        self.tree_detail.column("mapping", width=130, anchor="center")

        sb_y = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_detail.yview)
        self.tree_detail.configure(yscrollcommand=sb_y.set)

        self.tree_detail.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")

        # Eventi di selezione e click sui test
        self.tree_detail.bind("<Double-1>", self._on_detail_row_double_click)
        self.tree_detail.bind("<space>", self._on_detail_row_space)
        self.tree_detail.bind("<<TreeviewSelect>>", self._update_detail_focus_styles, add="+")
        self.tree_detail.bind("<FocusIn>", self._update_detail_focus_styles, add="+")
        self.tree_detail.bind("<FocusOut>", self._update_detail_focus_styles, add="+")

    def _configure_detail_row_styles(self) -> None:
        """Configura colori e font locali senza cambiare le altre tabelle.

        La riga attiva indica la posizione del cursore, non l'autorizzazione
        all'export: togliamo solo i colori associati a quello stato, lasciando
        intatti layout e navigazione da tastiera. Una sottolineatura locale
        segnala la riga con focus anche se il tema nativo usa solo il colore.
        """
        style = ttk.Style(self.tree_detail)
        for option in ("background", "foreground"):
            style.map("ExamDetail.Treeview", **{
                option: [entry for entry in style.map("Treeview", option)
                         if not any("selected" in str(state) for state in entry[:-1])]
            })

        # Copie locali: nessuna modifica al font condiviso TkDefaultFont.
        self._detail_normal_font = tkfont.Font(
            root=self, font=style.lookup("Treeview", "font") or "TkDefaultFont",
        )
        self._detail_selected_font = self._detail_normal_font.copy()
        self._detail_selected_font.configure(weight="bold")
        self._detail_focus_fonts: list[tkfont.Font] = []
        for tag, colors, font in (
            ("export_selected", {"background": COLOR_EXAM_SELECTED_BG,
                                 "foreground": COLOR_EXAM_SELECTED_TEXT}, self._detail_selected_font),
            ("already_sent", {"background": COLOR_EXAM_SENT_BG,
                              "foreground": COLOR_EXAM_SENT_TEXT}, self._detail_normal_font),
            ("pending", {}, self._detail_normal_font),
        ):
            self.tree_detail.tag_configure(tag, **colors, font=font)
            focus_font = font.copy()
            focus_font.configure(underline=True)
            self._detail_focus_fonts.append(focus_font)
            self.tree_detail.tag_configure(f"{tag}_focus", **colors, font=focus_font)

    def _update_detail_focus_styles(self, event: object = None) -> None:
        """Distingue il cursore dalle spunte senza cambiare selezioni o valori."""
        for row_id in self.tree_detail.get_children():
            self._update_detail_row_style(int(row_id))

    def _update_detail_row_style(self, result_id: int) -> None:
        """Aggiorna una riga usando gli stati esistenti, senza modificarli.

        La spunta prevale sullo stato Inviato per rendere evidente un reinvio;
        una riga pendente esclusa conserva invece l'aspetto normale del tema.
        """
        sample = self.selected_sample_for_detail
        if sample is None or not self.tree_detail.exists(str(result_id)):
            return
        if result_id in self.selected_tests_by_sample.get(sample.id, set()):
            tag = "export_selected"
        elif result_id in self._detail_exported_ids:
            tag = "already_sent"
        else:
            tag = "pending"
        if self.tree_detail.focus_get() == self.tree_detail and self.tree_detail.focus() == str(result_id):
            tag += "_focus"
        self.tree_detail.item(str(result_id), tags=(tag,))

    # =========================================================================
    # 5. FOOTER / ACTION BAR
    # =========================================================================
    def _build_footer(self, row: int) -> None:
        footer = ctk.CTkFrame(self, height=56, corner_radius=8)
        footer.grid(row=row, column=0, sticky="ew", padx=15, pady=(5, 12))

        # Contatori Statistiche
        self.lbl_stats = ctk.CTkLabel(
            footer,
            text="Caricamento statistiche...",
            font=FONT_NORMAL
        )
        self.lbl_stats.pack(side="left", padx=15, pady=10)

        # Pulsante Esporta
        self.btn_export = ctk.CTkButton(
            footer,
            text="📤 Esporta Selezionati per LIS",
            font=FONT_SUBTITLE,
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            height=40,
            command=self._handle_export_selected
        )
        self.btn_export.pack(side="right", padx=15, pady=8)

    # =========================================================================
    # LOGICA DI CARICAMENTO E FILTRO
    # =========================================================================
    def _get_current_filter(self) -> SampleFilter:
        search = self.entry_search.get().strip()

        st_val = self.combo_status.get()
        status_map = {
            "Da Esportare": "DA_ESPORTARE",
            "Esportati": "ESPORTATI",
            "Tutti": "TUTTI",
        }
        st_filter = status_map.get(st_val, "DA_ESPORTARE")

        dt_val = self.combo_date.get()
        date_map = {
            "Ultimo Mese": "MESE",
            "Ultimi 7 Giorni": "SETTIMANA",
            "Ultimi 3 Mesi": "TRE_MESI",
            "Anno Corrente": "ANNO",
            "Tutti": "TUTTI",
        }
        dt_filter = date_map.get(dt_val, "MESE")

        return SampleFilter(
            search_query=search,
            status_filter=st_filter,
            date_filter=dt_filter,
        )

    def _on_filter_changed(self) -> None:
        self._load_samples(preserve_selection=True)

    def _load_samples(self, preserve_selection: bool = False) -> None:
        filter_opts = self._get_current_filter()
        self.loaded_samples = self.db.get_samples(filter_opts)

        if not preserve_selection:
            # Per default seleziona tutti i campioni visibili (come da specifiche)
            self.selected_sample_ids = {s.id for s in self.loaded_samples if s.id is not None}
            self.selected_tests_by_sample = {}
        else:
            # Mantieni solo le selezioni ancora presenti tra i campioni caricati
            current_ids = {s.id for s in self.loaded_samples if s.id is not None}
            self.selected_sample_ids = self.selected_sample_ids.intersection(current_ids)
            self.selected_tests_by_sample = {
                s_id: test_set for s_id, test_set in self.selected_tests_by_sample.items() if s_id in current_ids
            }

        # Inizializza le spunte per TUTTI i campioni, anche senza aprirne il
        # dettaglio. Una selezione già esistente può soltanto perdere ID non
        # più presenti: nuovi risultati non devono ampliare un invio preparato.
        for sample in self.loaded_samples:
            if sample.id is None:
                continue
            results = self.db.get_sample_results(sample.id)
            available_ids = {r.id for r in results if r.id is not None}
            if sample.id in self.selected_tests_by_sample:
                self.selected_tests_by_sample[sample.id].intersection_update(available_ids)
            else:
                self.selected_tests_by_sample[sample.id] = {
                    r.id for r in results if r.id is not None and not r.is_exported
                }
            if not self.selected_tests_by_sample[sample.id]:
                self.selected_sample_ids.discard(sample.id)

        # Popola tabella Master
        for row in self.tree_master.get_children():
            self.tree_master.delete(row)

        for s in self.loaded_samples:
            is_sel = " [✓] " if s.id in self.selected_sample_ids else " [  ] "
            status_icon = "🟢 Esportato" if s.status == "ESPORTATO" else "🟠 Da Esportare"

            sel_tests = len(self.selected_tests_by_sample.get(s.id, set()))

            params_display = f"{sel_tests}/{s.results_count}"

            item_id = self.tree_master.insert(
                "",
                "end",
                iid=str(s.id),
                values=(
                    is_sel,
                    s.sample_code,
                    s.lab_code,
                    s.year,
                    s.acceptance,
                    s.conferment,
                    s.sample_number,
                    params_display,
                    s.imported_at or "-",
                    status_icon,
                )
            )

        self._update_stats_label()

        # Seleziona il primo elemento o mantieni quello attivo
        if self.loaded_samples:
            first_id = str(self.loaded_samples[0].id)
            self.tree_master.selection_set(first_id)
            self._display_sample_detail(self.loaded_samples[0])
        else:
            self._clear_detail_panel()

    def _update_stats_label(self) -> None:
        summary = self.db.get_summary_counts()
        sel_count = len(self.selected_sample_ids)
        visible_count = len(self.loaded_samples)

        sel_tests_total = sum(
            len(self.selected_tests_by_sample.get(s.id, set()))
            for s in self.loaded_samples
            if s.id in self.selected_sample_ids
        )

        self.lbl_stats.configure(
            text=f"Campioni a video: {visible_count}  |  "
                 f"Selezionati per export: {sel_count} ({sel_tests_total} test)  |  "
                 f"Totali nel DB: {summary['total']} (🟠 Da esportare: {summary['da_esportare']} - 🟢 Esportati: {summary['esportati']})"
        )

    # =========================================================================
    # GESTIONE SELEZIONE E DETTAGLIO
    # =========================================================================
    def _on_master_row_selected(self, event) -> None:
        sel = self.tree_master.selection()
        if not sel:
            return
        sample_id = int(sel[0])
        matching = [s for s in self.loaded_samples if s.id == sample_id]
        if matching:
            self._display_sample_detail(matching[0])

    def _display_sample_detail(self, sample: SampleRecord) -> None:
        self.selected_sample_for_detail = sample
        self.lbl_detail_title.configure(
            text=f"🔬 Parametri del Campione: {sample.sample_code} (Accettazione: {sample.acceptance} - Lab: {sample.lab_code})"
        )

        for row in self.tree_detail.get_children():
            self.tree_detail.delete(row)

        results = self.db.get_sample_results(sample.id) # type: ignore
        self._detail_exported_ids = {
            r.id for r in results if r.id is not None and r.is_exported
        }

        # Aprire un dettaglio visualizza le spunte già preparate al caricamento:
        # la navigazione fra campioni non modifica ciò che verrà esportato.
        selected_test_ids = self.selected_tests_by_sample.get(sample.id, set())

        for r in results:
            is_sel = " [✓] " if r.id in selected_test_ids else " [  ] "
            status_lis = "🟢 Inviato" if r.is_exported else "🟠 Da Inviare"
            mapping_status = "✅ Valido" if r.is_mapped else "⚠️ Non Mappato"
            self.tree_detail.insert(
                "",
                "end",
                iid=str(r.id),
                values=(
                    is_sel,
                    status_lis,
                    r.param_name,
                    r.lis_exam_code or "---",
                    r.lis_substance_code or "",
                    r.raw_value,
                    r.formatted_value,
                    mapping_status
                )
            )
            if r.id is not None:
                self._update_detail_row_style(r.id)

    def _clear_detail_panel(self) -> None:
        self.selected_sample_for_detail = None
        self._detail_exported_ids.clear()
        self.lbl_detail_title.configure(text="🔬 Parametri e Risultati Analitici (Nessun campione presente)")
        for row in self.tree_detail.get_children():
            self.tree_detail.delete(row)

    # -------------------------------------------------------------------------
    # Selezione Test / Parametri nel Dettaglio
    # -------------------------------------------------------------------------
    def _on_detail_row_double_click(self, event) -> None:
        sel = self.tree_detail.selection()
        if sel:
            self._toggle_test_selection(int(sel[0]))

    def _on_detail_row_space(self, event) -> None:
        sel = self.tree_detail.selection()
        if sel:
            self._toggle_test_selection(int(sel[0]))

    def _toggle_test_selection(self, test_id: int) -> None:
        sample = self.selected_sample_for_detail
        if not sample or sample.id is None:
            return

        if sample.id not in self.selected_tests_by_sample:
            results = self.db.get_sample_results(sample.id)
            self.selected_tests_by_sample[sample.id] = {r.id for r in results if r.id is not None and not r.is_exported}

        test_set = self.selected_tests_by_sample[sample.id]
        if test_id in test_set:
            test_set.remove(test_id)
            new_val = " [  ] "
        else:
            test_set.add(test_id)
            new_val = " [✓] "

        # Aggiorna la riga nel detail treeview
        if self.tree_detail.exists(str(test_id)):
            vals = list(self.tree_detail.item(str(test_id))["values"])
            vals[0] = new_val
            self.tree_detail.item(str(test_id), values=vals)
            self._update_detail_row_style(test_id)

        # Sincronizza stato con la tabella Master
        self._sync_sample_with_test_selection(sample.id)

    def _sync_sample_with_test_selection(self, sample_id: int) -> None:
        sample = next((s for s in self.loaded_samples if s.id == sample_id), None)
        if not sample:
            return

        test_set = self.selected_tests_by_sample.get(sample_id, set())
        sel_count = len(test_set)
        total_count = sample.results_count

        if not self.tree_master.exists(str(sample_id)):
            return

        m_vals = list(self.tree_master.item(str(sample_id))["values"])
        m_vals[7] = f"{sel_count}/{total_count}"

        # Se 0 test selezionati, escludi e deseleziona il campione nella tabella superiore
        if sel_count == 0:
            self.selected_sample_ids.discard(sample_id)
            m_vals[0] = " [  ] "
        else:
            # Se ha almeno 1 test selezionato ed era deselezionato perché a 0 test, riseleziona il campione
            if sample_id not in self.selected_sample_ids and sel_count == 1:
                self.selected_sample_ids.add(sample_id)
                m_vals[0] = " [✓] "

        self.tree_master.item(str(sample_id), values=m_vals)
        self._update_stats_label()

    def _select_all_tests_current_sample(self) -> None:
        sample = self.selected_sample_for_detail
        if not sample or sample.id is None:
            return

        results = self.db.get_sample_results(sample.id)
        self.selected_tests_by_sample[sample.id] = {r.id for r in results if r.id is not None}

        for r in results:
            if r.id is not None and self.tree_detail.exists(str(r.id)):
                vals = list(self.tree_detail.item(str(r.id))["values"])
                vals[0] = " [✓] "
                self.tree_detail.item(str(r.id), values=vals)
                self._update_detail_row_style(r.id)

        # Assicura che il campione sia selezionato anche nel Master
        self.selected_sample_ids.add(sample.id)
        if self.tree_master.exists(str(sample.id)):
            m_vals = list(self.tree_master.item(str(sample.id))["values"])
            m_vals[0] = " [✓] "
            m_vals[7] = f"{len(results)}/{sample.results_count}"
            self.tree_master.item(str(sample.id), values=m_vals)

        self._update_stats_label()

    def _deselect_all_tests_current_sample(self) -> None:
        sample = self.selected_sample_for_detail
        if not sample or sample.id is None:
            return

        self.selected_tests_by_sample[sample.id] = set()

        for r_id in self.tree_detail.get_children():
            vals = list(self.tree_detail.item(r_id)["values"])
            vals[0] = " [  ] "
            self.tree_detail.item(r_id, values=vals)
            self._update_detail_row_style(int(r_id))

        # Se 0 test, deseleziona automaticamente il campione nel Master
        self.selected_sample_ids.discard(sample.id)
        if self.tree_master.exists(str(sample.id)):
            m_vals = list(self.tree_master.item(str(sample.id))["values"])
            m_vals[0] = " [  ] "
            m_vals[7] = f"0/{sample.results_count}"
            self.tree_master.item(str(sample.id), values=m_vals)

        self._update_stats_label()

    # -------------------------------------------------------------------------
    # Selezione Campioni nel Master
    # -------------------------------------------------------------------------
    def _toggle_sample_selection(self, sample_id: int) -> None:
        sample = next((s for s in self.loaded_samples if s.id == sample_id), None)
        if not sample:
            return

        if sample_id in self.selected_sample_ids:
            self.selected_sample_ids.remove(sample_id)
            new_val = " [  ] "
        else:
            # Se il campione aveva 0 test selezionati, riseleziona tutti i test per consentire l'export
            if sample_id in self.selected_tests_by_sample and len(self.selected_tests_by_sample[sample_id]) == 0:
                results = self.db.get_sample_results(sample_id)
                self.selected_tests_by_sample[sample_id] = {r.id for r in results if r.id is not None}
                if self.selected_sample_for_detail and self.selected_sample_for_detail.id == sample_id:
                    self._display_sample_detail(self.selected_sample_for_detail)

            self.selected_sample_ids.add(sample_id)
            new_val = " [✓] "

        # Aggiorna la riga del treeview master
        if self.tree_master.exists(str(sample_id)):
            item = self.tree_master.item(str(sample_id))
            vals = list(item["values"])
            vals[0] = new_val
            sel_tests = len(self.selected_tests_by_sample.get(sample_id, set()))
            vals[7] = f"{sel_tests}/{sample.results_count}"
            self.tree_master.item(str(sample_id), values=vals)

        self._update_stats_label()

    def _on_master_row_double_click(self, event) -> None:
        sel = self.tree_master.selection()
        if sel:
            self._toggle_sample_selection(int(sel[0]))

    def _on_master_row_space(self, event) -> None:
        sel = self.tree_master.selection()
        if sel:
            self._toggle_sample_selection(int(sel[0]))

    def _select_all_visible(self) -> None:
        for s in self.loaded_samples:
            if s.id is not None:
                self.selected_sample_ids.add(s.id)
                # Se tutti i test erano stati deselezionati, riselezionali tutti
                if s.id in self.selected_tests_by_sample and len(self.selected_tests_by_sample[s.id]) == 0:
                    results = self.db.get_sample_results(s.id)
                    self.selected_tests_by_sample[s.id] = {r.id for r in results if r.id is not None}

                sel_tests = len(self.selected_tests_by_sample.get(s.id, set()))

                if self.tree_master.exists(str(s.id)):
                    item = self.tree_master.item(str(s.id))
                    vals = list(item["values"])
                    vals[0] = " [✓] "
                    vals[7] = f"{sel_tests}/{s.results_count}"
                    self.tree_master.item(str(s.id), values=vals)

        if self.selected_sample_for_detail:
            self._display_sample_detail(self.selected_sample_for_detail)
        self._update_stats_label()

    def _deselect_all_visible(self) -> None:
        for s in self.loaded_samples:
            if s.id is not None and s.id in self.selected_sample_ids:
                self.selected_sample_ids.remove(s.id)
                if self.tree_master.exists(str(s.id)):
                    item = self.tree_master.item(str(s.id))
                    vals = list(item["values"])
                    vals[0] = " [  ] "
                    self.tree_master.item(str(s.id), values=vals)
        self._update_stats_label()

    # =========================================================================
    # IMPORTAZIONE FILE
    # =========================================================================
    def _handle_import_files(self) -> None:
        config = self.db.get_config()

        # Importazione automatica con Unione Intelligente (Merge) senza popup bloccanti per duplicato
        summary = self.importer_service.import_all(config)

        # Registra nel log di audit
        self.db.log_action(
            self.current_user.id,
            self.current_user.username,
            "IMPORT_FILES",
            f"Totali: {summary.total_files_found}, Nuovi: {summary.imported_count}, Integrati: {summary.merged_count}, Duplicati: {summary.duplicate_count}, Errori: {summary.error_count}"
        )

        self._load_samples()

        # Mostra riepilogo
        if summary.total_files_found == 0:
            messagebox.showinfo("Importazione File", f"Nessun file trovato nella cartella:\n{config.input_dir}", parent=self)
        else:
            msg = (
                f"Elaborazione completata!\n\n"
                f"• File trovati: {summary.total_files_found}\n"
                f"• Nuovi campioni importati: {summary.imported_count}\n"
            )
            if summary.merged_count > 0:
                msg += f"• Campioni integrati con nuovi test: {summary.merged_count}\n"
            if summary.duplicate_count > 0:
                msg += f"• Campioni già presenti (invariati): {summary.duplicate_count}\n"
            if summary.skipped_count > 0:
                msg += f"• Campioni saltati: {summary.skipped_count}\n"
            if summary.error_count > 0:
                msg += f"• Errori / Non conformi: {summary.error_count}\n"

            if summary.unmapped_params_global:
                msg += f"\n⚠️ Parametri non presenti in transcodifica:\n{', '.join(sorted(summary.unmapped_params_global))}"

            if summary.messages:
                msg += "\n\nInformazioni:\n" + "\n".join(summary.messages)
            if summary.warnings:
                msg += "\n\nRighe scartate:\n" + "\n".join(summary.warnings)
            # Riporta anche la causa degli errori globali (es. intestazioni
            # ambigue), così l'operatore sa cosa correggere prima di riprovare.
            errors = [f"{item.filename}: {item.message}" for item in summary.items if item.status == "ERROR"]
            if errors:
                msg += "\n\nDettagli errori:\n" + "\n".join(errors)

            if summary.error_count > 0 or summary.warnings:
                messagebox.showwarning("Riepilogo Importazione", msg, parent=self)
            else:
                messagebox.showinfo("Riepilogo Importazione", msg, parent=self)

    # =========================================================================
    # ESPORTAZIONE LIS
    # =========================================================================
    def _handle_export_selected(self) -> None:
        if not self.selected_sample_ids:
            messagebox.showwarning("Esportazione LIS", "Nessun campione selezionato per l'esportazione.", parent=self)
            return

        # Recupera i campioni completi di parametri, filtrando solo i test selezionati
        samples_to_export: List[SampleRecord] = []
        for s_id in self.selected_sample_ids:
            s_full = self.db.get_sample_with_results(s_id)
            if not s_full:
                continue

            # Il filtro è sempre obbligatorio: una selezione assente o vuota
            # non autorizza l'invio di altri risultati recuperati dal database.
            selected_test_ids = self.selected_tests_by_sample.get(s_id, set())
            s_full.results = [r for r in s_full.results if r.id in selected_test_ids]

            if s_full.results:
                samples_to_export.append(s_full)

        if not samples_to_export:
            messagebox.showwarning("Esportazione LIS", "Nessun test selezionato nei campioni scelti.", parent=self)
            return

        config = self.db.get_config()
        ok, msg, out_file, count = self.exporter.export_samples(samples_to_export, config.export_dir)

        if ok:
            self.db.log_action(
                self.current_user.id,
                self.current_user.username,
                "EXPORT_LIS",
                f"File: {out_file.name} - {msg}"
            )
            messagebox.showinfo(
                "Esportazione Completata",
                f"File CSV generato con successo per il LIS!\n\n"
                f"• Destinazione: {out_file}\n"
                f"\n{msg}",
                parent=self
            )
            self._load_samples(preserve_selection=True)
        else:
            messagebox.showerror("Errore Esportazione", msg, parent=self)

    # =========================================================================
    # APERTURA DIALOGHI E GESTIONE CONFIGURAZIONE
    # =========================================================================
    def update_version_display(self) -> None:
        """Aggiorna l'etichetta del titolo interno e il titolo della finestra principale."""
        config = self.db.get_config()
        if hasattr(self, "lbl_brand") and self.lbl_brand.winfo_exists():
            self.lbl_brand.configure(text=f"🔬 STRUMENTI ➔ LIS v{config.app_version}")

        if hasattr(self.master, "update_app_title"):
            self.master.update_app_title()
        elif hasattr(self.master, "title"):
            self.master.title(f"Interfaccia Strumenti di Laboratorio - LIS - Versione {config.app_version}")

    def _on_settings_updated(self) -> None:
        """Callback invocata alla modifica delle impostazioni."""
        self.update_version_display()
        self._load_samples()

    def _open_settings_dialog(self) -> None:
        SettingsDialog(self.master, self.db, on_config_changed=self._on_settings_updated)

    def _open_maintenance_dialog(self) -> None:
        SettingsDialog(
            self.master,
            self.db,
            on_config_changed=self._on_settings_updated,
            default_tab="🧹 Manutenzione Dati"
        )

    def _open_password_dialog(self) -> None:
        PasswordDialog(self.master, self.db, self.current_user)

    def _open_help_dialog(self) -> None:
        HelpDialog(self.master)
