# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Dialogo Modale delle Configurazioni e Gestione Utenti (Amministrazione)."""

from __future__ import annotations

import customtkinter as ctk
from datetime import datetime, timedelta
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, List, Optional

from src.auth import SessionManager
from src.config import AppConfig
from src.database import Database
from src.gui.theme import (
    COLOR_DANGER,
    COLOR_DANGER_HOVER,
    COLOR_PRIMARY,
    COLOR_PRIMARY_HOVER,
    COLOR_SUCCESS,
    COLOR_SUCCESS_HOVER,
    FONT_NORMAL,
    FONT_SECTION,
    FONT_SMALL,
    FONT_SUBTITLE,
    FONT_TITLE,
)
from src.models import SampleRecord
from driver import get_available_driver_names


class SettingsDialog(ctk.CTkToplevel):
    """Pannello di configurazione avanzata accessibile solo all'Amministratore."""

    def __init__(
        self,
        parent: ctk.CTk,
        db: Database,
        on_config_changed: Optional[Callable[[], None]] = None,
        default_tab: Optional[str] = None
    ):
        super().__init__(parent)
        self.db = db
        self.on_config_changed = on_config_changed
        self.default_tab = default_tab

        # Stato dell'ordinamento per le griglie Transcodifiche e Gestione Utenti
        self._trans_sort: dict[str, Any] = {"col": None, "reverse": False}
        self._users_sort: dict[str, Any] = {"col": None, "reverse": False}
        self.trans_col_titles: dict[str, str] = {}
        self.users_col_titles: dict[str, str] = {}

        # Cache campioni per la scheda manutenzione
        self._maint_samples_cache: List[SampleRecord] = []

        # Verifica di sicurezza: solo gli utenti con ruolo ADMIN possono accedere alle configurazioni
        if not SessionManager.is_admin():
            messagebox.showerror(
                "Accesso Negato",
                "Solo gli utenti con ruolo Amministratore possono accedere e modificare le impostazioni di sistema.",
                parent=parent
            )
            self.destroy()
            return

        self.title("Configurazione di Sistema - Strumenti LIS")
        self.geometry("820x620")
        self.minsize(750, 550)
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

    def _create_widgets(self) -> None:
        # Intestazione
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 10))

        lbl_title = ctk.CTkLabel(header_frame, text="⚙️ Impostazioni e Configurazione", font=FONT_TITLE)
        lbl_title.pack(side="left")

        # Tabview
        self.tabview = ctk.CTkTabview(self, corner_radius=10)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        tab_driver = self.tabview.add("🔬 Driver Strumento")
        tab_paths = self.tabview.add("📁 Percorsi Cartelle")
        tab_trans = self.tabview.add("🔄 Transcodifiche LIS")
        tab_users = self.tabview.add("👥 Gestione Utenti")
        tab_labs = self.tabview.add("🏥 Codici Laboratorio")
        tab_maint = self.tabview.add("🧹 Manutenzione Dati")

        self._build_tab_driver(tab_driver)
        self._build_tab_paths(tab_paths)
        self._build_tab_transcodings(tab_trans)
        self._build_tab_users(tab_users)
        self._build_tab_labs(tab_labs)
        self._build_tab_maintenance(tab_maint)

        if self.default_tab and self.default_tab in self.tabview._tab_dict:
            self.tabview.set(self.default_tab)

    # =========================================================================
    # TAB: DRIVER STRUMENTO PREDEFINITO
    # =========================================================================
    def _build_tab_driver(self, tab: ctk.CTkFrame) -> None:
        config = self.db.get_config()
        available_drivers = get_available_driver_names()

        lbl_desc = ctk.CTkLabel(
            tab,
            text="Seleziona il driver dello strumento analitico da utilizzare come predefinito per l'acquisizione dei file:\n"
                 "(Solo gli utenti con ruolo Amministratore possono modificare questa impostazione)",
            font=FONT_NORMAL,
            text_color="gray",
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=25, pady=(20, 15))

        card = ctk.CTkFrame(tab, corner_radius=10)
        card.pack(fill="x", padx=25, pady=(0, 20))

        ctk.CTkLabel(
            card,
            text="Strumento / Driver di Default:",
            font=FONT_SECTION
        ).pack(anchor="w", padx=20, pady=(15, 8))

        # Selettore ComboBox
        self.combo_driver = ctk.CTkComboBox(
            card,
            values=available_drivers,
            font=FONT_NORMAL,
            width=500,
            height=38,
            state="readonly",
            command=self._on_driver_selected
        )
        # Seleziona il driver configurato se presente, altrimenti il primo
        current_drv = config.default_driver if config.default_driver in available_drivers else available_drivers[0]
        self.combo_driver.set(current_drv)
        self.combo_driver.pack(anchor="w", padx=20, pady=(0, 15))

        # Box informativo sul driver selezionato
        self.lbl_driver_info = ctk.CTkLabel(
            card,
            text="",
            font=FONT_SMALL,
            text_color="gray",
            justify="left"
        )
        self.lbl_driver_info.pack(anchor="w", padx=20, pady=(0, 15))
        self._update_driver_info_text(current_drv)

        # Pulsante Salva Driver
        btn_save_drv = ctk.CTkButton(
            tab,
            text="💾 Salva Driver Predefinito",
            font=FONT_SUBTITLE,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            height=38,
            command=self._save_default_driver
        )
        btn_save_drv.pack(anchor="w", padx=25)

    def _on_driver_selected(self, choice: str) -> None:
        self._update_driver_info_text(choice)

    def _update_driver_info_text(self, driver_name: str) -> None:
        info_map = {
            "Cromatografo Ionico (Dionex / IC)": (
                "• Formato: File di testo (.txt) con delimitatore di tabulazione\n"
                "• Struttura: 'Sample Name:' alla prima riga, tabella 'Component / Amount' dalla riga 9+\n"
                "• Parametri supportati: Fluoruri, Cloriti, Cloruri, Nitriti, Clorati, Nitrati, Solfati\n"
                "• Conversione: Valori 'n.a.' o non numerici convertiti a 0, virgola decimale per il LIS."
            ),
            "Spettrofotometro (UV-Vis / Assorbanza)": (
                "• Formato: File di testo / CSV tabulari o delimitati con letture di assorbanza\n"
                "• Struttura: Coppie 'Parametro / Valore' per spettrofotometri e lettori di micropiastre\n"
                "• Conversione: Estrazione automatica e mappatura con i codici LIS registrati."
            ),
        }
        desc = info_map.get(
            driver_name,
            f"• Driver registrato nel modulo driver.py: '{driver_name}'\n"
            f"• Conforme all'interfaccia BaseInstrumentDriver per l'acquisizione analitica."
        )
        self.lbl_driver_info.configure(text=desc)

    def _save_default_driver(self) -> None:
        if not SessionManager.is_admin():
            messagebox.showerror("Errore", "Solo gli amministratori possono modificare il driver di default.", parent=self)
            return

        chosen_driver = self.combo_driver.get().strip()
        if not chosen_driver:
            messagebox.showerror("Errore", "Seleziona un driver valido", parent=self)
            return

        self.db.save_config_value("default_driver", chosen_driver, "Nome dello strumento analitico / driver di default")
        curr_user = SessionManager.get_user()
        self.db.log_action(
            curr_user.id if curr_user else None,
            curr_user.username if curr_user else "admin",
            "CONFIG_DRIVER_UPDATE",
            f"Driver predefinito impostato a: {chosen_driver}"
        )
        if self.on_config_changed:
            self.on_config_changed()

        messagebox.showinfo(
            "Driver Aggiornato",
            f"Il driver di default è stato impostato su:\n\n'{chosen_driver}'\n\n"
            f"Verrà utilizzato per tutte le prossime acquisizioni di file.",
            parent=self
        )

    # =========================================================================
    # TAB 1: PERCORSI CARTELLE
    # =========================================================================
    def _build_tab_paths(self, tab: ctk.CTkFrame) -> None:
        config = self.db.get_config()

        lbl_desc = ctk.CTkLabel(
            tab,
            text="Configura le cartelle di lavoro utilizzate per l'acquisizione, archiviazione ed esportazione:",
            font=FONT_NORMAL,
            text_color="gray"
        )
        lbl_desc.pack(anchor="w", padx=20, pady=(15, 15))

        form_frame = ctk.CTkFrame(tab, fg_color="transparent")
        form_frame.pack(fill="x", padx=20)

        # 1. Cartella Ingressi (Sequenze)
        self.entry_input = self._create_path_row(form_frame, "Cartella File Strumenti (Ingresso):", str(config.input_dir), 0)

        # 2. Cartella Archivio Elaborati
        self.entry_archive = self._create_path_row(form_frame, "Cartella File Archiviati (Elaborati con successo):", str(config.archive_dir), 1)

        # 3. Cartella Errori
        self.entry_error = self._create_path_row(form_frame, "Cartella File Scartati (Errori / Non conformi):", str(config.error_dir), 2)

        # 4. Cartella Esportazione LIS (Default)
        self.entry_export = self._create_path_row(form_frame, "Cartella File Esportati per il LIS (Default):", str(config.export_dir), 3)

        # Pulsante Salva Percorsi
        btn_save = ctk.CTkButton(
            tab,
            text="💾 Salva Percorsi",
            font=FONT_SUBTITLE,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            height=38,
            command=self._save_paths
        )
        btn_save.pack(anchor="e", padx=20, pady=(15, 10))

        # Sezione Versione Software dell'Applicazione
        card_version = ctk.CTkFrame(tab, corner_radius=10)
        card_version.pack(fill="x", padx=20, pady=(10, 15))

        ctk.CTkLabel(
            card_version,
            text="Versione Software dell'Applicazione:",
            font=FONT_SECTION
        ).pack(anchor="w", padx=20, pady=(12, 4))

        ctk.CTkLabel(
            card_version,
            text="Visualizzata nella barra del titolo della finestra principale e nella testata della dashboard.",
            font=FONT_SMALL,
            text_color="gray"
        ).pack(anchor="w", padx=20, pady=(0, 10))

        row_v = ctk.CTkFrame(card_version, fg_color="transparent")
        row_v.pack(fill="x", padx=20, pady=(0, 12))

        self.entry_version = ctk.CTkEntry(
            row_v,
            font=FONT_NORMAL,
            width=200,
            height=34
        )
        self.entry_version.insert(0, config.app_version)
        self.entry_version.pack(side="left", padx=(0, 12))

        btn_save_version = ctk.CTkButton(
            row_v,
            text="💾 Salva Versione",
            font=FONT_SMALL,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            height=34,
            width=130,
            command=self._save_version
        )
        btn_save_version.pack(side="left")

    def _create_path_row(self, parent: ctk.CTkFrame, label: str, default_val: str, row: int) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=FONT_NORMAL).grid(row=row*2, column=0, sticky="w", pady=(8, 2))
        entry = ctk.CTkEntry(parent, font=FONT_NORMAL, width=540)
        entry.insert(0, default_val)
        entry.grid(row=row*2+1, column=0, sticky="ew", padx=(0, 10), pady=(0, 8))

        btn_browse = ctk.CTkButton(
            parent,
            text="Sfoglia...",
            width=100,
            command=lambda: self._browse_dir(entry)
        )
        btn_browse.grid(row=row*2+1, column=1, pady=(0, 8))
        parent.grid_columnconfigure(0, weight=1)
        return entry

    def _browse_dir(self, entry: ctk.CTkEntry) -> None:
        selected = filedialog.askdirectory(initialdir=entry.get(), parent=self)
        if selected:
            entry.delete(0, "end")
            entry.insert(0, selected)

    def _save_paths(self) -> None:
        new_version = self.entry_version.get().strip() or "1.0"
        cfg = AppConfig(
            input_dir=self.entry_input.get().strip(),
            archive_dir=self.entry_archive.get().strip(),
            error_dir=self.entry_error.get().strip(),
            export_dir=self.entry_export.get().strip(),
            app_version=new_version,
        )
        cfg.ensure_directories()
        self.db.save_all_configs(cfg)
        curr_user = SessionManager.get_user()
        self.db.log_action(curr_user.id if curr_user else None, curr_user.username if curr_user else "admin", "CONFIG_PATHS_UPDATE")
        if self.on_config_changed:
            self.on_config_changed()
        messagebox.showinfo("Configurazione", "Percorsi cartelle salvati con successo!", parent=self)

    def _save_version(self) -> None:
        """Salva la nuova versione dell'applicazione e aggiorna l'interfaccia."""
        new_version = self.entry_version.get().strip()
        if not new_version:
            messagebox.showwarning(
                "Versione non valida",
                "Il campo della versione non può essere lasciato vuoto.",
                parent=self
            )
            return

        self.db.save_config_value("app_version", new_version, "Versione del software dell'applicazione")
        curr_user = SessionManager.get_user()
        self.db.log_action(
            curr_user.id if curr_user else None,
            curr_user.username if curr_user else "admin",
            "CONFIG_VERSION_UPDATE",
            f"Versione aggiornata a: {new_version}"
        )

        if self.on_config_changed:
            self.on_config_changed()

        messagebox.showinfo(
            "Versione Aggiornata",
            f"La versione del software è stata aggiornata a:\n\n'Versione {new_version}'\n\n"
            f"Il titolo della finestra principale è stato aggiornato.",
            parent=self
        )

    # =========================================================================
    # TAB 2: TRANSCODIFICHE LIS
    # =========================================================================
    def _build_tab_transcodings(self, tab: ctk.CTkFrame) -> None:
        # Toolbar
        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(fill="x", padx=15, pady=(10, 5))

        btn_add = ctk.CTkButton(
            toolbar,
            text="➕ Nuova Regola",
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            width=130,
            command=self._show_add_transcoding_dialog
        )
        btn_add.pack(side="left", padx=(0, 10))

        btn_edit = ctk.CTkButton(
            toolbar,
            text="✏️ Modifica Regola",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            width=130,
            command=self._show_edit_transcoding_dialog
        )
        btn_edit.pack(side="left", padx=(0, 10))

        btn_del = ctk.CTkButton(
            toolbar,
            text="🗑️ Elimina Regola",
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            width=130,
            command=self._delete_selected_transcoding
        )
        btn_del.pack(side="left", padx=(0, 10))

        btn_import_txt = ctk.CTkButton(
            toolbar,
            text="📥 Importa da TXT",
            width=130,
            command=self._import_transcodings_from_file
        )
        btn_import_txt.pack(side="right", padx=(5, 0))

        btn_export_txt = ctk.CTkButton(
            toolbar,
            text="📤 Esporta su TXT",
            width=130,
            command=self._export_transcodings_to_file
        )
        btn_export_txt.pack(side="right", padx=(5, 5))

        # Suggerimento ordinamento
        ctk.CTkLabel(
            tab,
            text="💡 Clicca sull'intestazione di qualsiasi colonna per ordinare la tabella (ascendente / discendente).",
            font=FONT_SMALL,
            text_color="gray"
        ).pack(anchor="w", padx=15, pady=(2, 0))

        # Tabella Regole con Treeview
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(4, 10))

        self.trans_col_titles = {
            "id": "ID",
            "param": "Parametro Strumento",
            "lis_code": "Codice Esame LIS",
            "desc": "Descrizione",
            "updated": "Ultimo Aggiornamento",
        }
        columns = tuple(self.trans_col_titles.keys())
        self.tree_trans = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        for col, title in self.trans_col_titles.items():
            self.tree_trans.heading(
                col,
                text=title,
                command=lambda c=col: self._on_sort_column(self.tree_trans, c, self.trans_col_titles, self._trans_sort)
            )

        self.tree_trans.column("id", width=40, anchor="center")
        self.tree_trans.column("param", width=180, anchor="w")
        self.tree_trans.column("lis_code", width=140, anchor="center")
        self.tree_trans.column("desc", width=200, anchor="w")
        self.tree_trans.column("updated", width=150, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_trans.yview)
        self.tree_trans.configure(yscrollcommand=scrollbar.set)

        self.tree_trans.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Supporto doppio clic per aprire direttamente la modifica della regola selezionata
        self.tree_trans.bind("<Double-1>", self._on_trans_double_click)

        self._refresh_transcodings_list()

    def _on_trans_double_click(self, event) -> None:
        """Apre la modifica solo se il doppio clic è avvenuto su una riga della tabella."""
        region = self.tree_trans.identify_region(event.x, event.y)
        if region in ("cell", "tree"):
            self._show_edit_transcoding_dialog()

    def _refresh_transcodings_list(self) -> None:
        for row in self.tree_trans.get_children():
            self.tree_trans.delete(row)
        rules = self.db.get_all_transcodings()
        for r in rules:
            self.tree_trans.insert("", "end", values=(
                r.id,
                r.instrument_param_name,
                r.lis_exam_code,
                r.description,
                r.updated_at or "-"
            ))
        if self._trans_sort.get("col"):
            self._apply_tree_sort(self.tree_trans, self._trans_sort["col"], self.trans_col_titles, self._trans_sort["reverse"])

    def _show_add_transcoding_dialog(self) -> None:
        dlg = ctk.CTkToplevel(self)
        dlg.title("Nuova Transcodifica")
        dlg.geometry("380x300")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Parametro Strumento (es. Fluoruri):", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(20, 2))
        entry_p = ctk.CTkEntry(dlg, font=FONT_NORMAL)
        entry_p.pack(fill="x", padx=25, pady=(0, 10))

        ctk.CTkLabel(dlg, text="Codice Esame LIS (es. BG00594):", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(5, 2))
        entry_c = ctk.CTkEntry(dlg, font=FONT_NORMAL)
        entry_c.pack(fill="x", padx=25, pady=(0, 10))

        ctk.CTkLabel(dlg, text="Descrizione opzionale:", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(5, 2))
        entry_d = ctk.CTkEntry(dlg, font=FONT_NORMAL)
        entry_d.pack(fill="x", padx=25, pady=(0, 15))

        def save():
            p, c, d = entry_p.get(), entry_c.get(), entry_d.get()
            ok, msg = self.db.save_transcoding(p, c, d)
            if ok:
                curr_user = SessionManager.get_user()
                self.db.log_action(
                    curr_user.id if curr_user else None,
                    curr_user.username if curr_user else "admin",
                    "CONFIG_TRANSCODING_ADD",
                    f"Aggiunta/aggiornata regola: {p} -> {c}"
                )
                self._refresh_transcodings_list()
                if self.on_config_changed:
                    self.on_config_changed()
                dlg.destroy()
            else:
                messagebox.showerror("Errore", msg, parent=dlg)

        btn_s = ctk.CTkButton(dlg, text="Salva Regola", fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, command=save)
        btn_s.pack(fill="x", padx=25, pady=(5, 10))

    def _show_edit_transcoding_dialog(self) -> None:
        """Apre il dialogo modale per modificare la regola di transcodifica selezionata."""
        sel = self.tree_trans.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona una regola da modificare", parent=self)
            return

        item = self.tree_trans.item(sel[0])
        vals = item["values"]
        rule_id = int(vals[0])
        current_param = str(vals[1])
        current_lis = str(vals[2])
        current_desc = str(vals[3]) if vals[3] != "-" else ""

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Modifica Transcodifica - {current_param}")
        dlg.geometry("380x300")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Parametro Strumento (es. Fluoruri):", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(20, 2))
        entry_p = ctk.CTkEntry(dlg, font=FONT_NORMAL)
        entry_p.insert(0, current_param)
        entry_p.pack(fill="x", padx=25, pady=(0, 10))

        ctk.CTkLabel(dlg, text="Codice Esame LIS (es. BG00594):", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(5, 2))
        entry_c = ctk.CTkEntry(dlg, font=FONT_NORMAL)
        entry_c.insert(0, current_lis)
        entry_c.pack(fill="x", padx=25, pady=(0, 10))

        ctk.CTkLabel(dlg, text="Descrizione opzionale:", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(5, 2))
        entry_d = ctk.CTkEntry(dlg, font=FONT_NORMAL)
        entry_d.insert(0, current_desc)
        entry_d.pack(fill="x", padx=25, pady=(0, 15))

        def save():
            p, c, d = entry_p.get(), entry_c.get(), entry_d.get()
            ok, msg = self.db.update_transcoding(rule_id, p, c, d)
            if ok:
                curr_user = SessionManager.get_user()
                self.db.log_action(
                    curr_user.id if curr_user else None,
                    curr_user.username if curr_user else "admin",
                    "CONFIG_TRANSCODING_UPDATE",
                    f"Modificata regola ID {rule_id}: {p} -> {c}"
                )
                self._refresh_transcodings_list()
                if self.on_config_changed:
                    self.on_config_changed()
                dlg.destroy()
            else:
                messagebox.showerror("Errore", msg, parent=dlg)

        btn_s = ctk.CTkButton(
            dlg,
            text="💾 Salva Modifiche",
            font=FONT_NORMAL,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=save
        )
        btn_s.pack(fill="x", padx=25, pady=(5, 10))

    def _delete_selected_transcoding(self) -> None:
        sel = self.tree_trans.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona una regola da eliminare", parent=self)
            return
        item = self.tree_trans.item(sel[0])
        rule_id = int(item["values"][0])
        rule_name = item["values"][1]

        if messagebox.askyesno("Conferma", f"Eliminare la transcodifica per '{rule_name}'?", parent=self):
            self.db.delete_transcoding(rule_id)
            curr_user = SessionManager.get_user()
            self.db.log_action(
                curr_user.id if curr_user else None,
                curr_user.username if curr_user else "admin",
                "CONFIG_TRANSCODING_DELETE",
                f"Eliminata regola ID {rule_id}: {rule_name}"
            )
            self._refresh_transcodings_list()
            if self.on_config_changed:
                self.on_config_changed()

    def _import_transcodings_from_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Seleziona file transcodifica TXT",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            parent=self
        )
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            count = 0
            for line in lines:
                line = line.strip()
                if not line or ":" not in line:
                    continue
                parts = line.split(":", 1)
                p_name = parts[0].strip()
                l_code = parts[1].strip()
                if p_name and l_code:
                    self.db.save_transcoding(p_name, l_code)
                    count += 1
            self._refresh_transcodings_list()
            messagebox.showinfo("Importazione", f"Importate {count} regole con successo!", parent=self)
        except Exception as ex:
            messagebox.showerror("Errore", f"Impossibile leggere il file: {ex}", parent=self)

    def _export_transcodings_to_file(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Salva file transcodifica TXT",
            defaultextension=".txt",
            initialfile="transcodifica.txt",
            filetypes=[("Text files", "*.txt")],
            parent=self
        )
        if not file_path:
            return
        try:
            rules = self.db.get_all_transcodings()
            with open(file_path, "w", encoding="utf-8") as f:
                for r in rules:
                    f.write(f"{r.instrument_param_name}:{r.lis_exam_code}\n")
            messagebox.showinfo("Esportazione", f"Esportate {len(rules)} regole su file!", parent=self)
        except Exception as ex:
            messagebox.showerror("Errore", f"Impossibile salvare il file: {ex}", parent=self)

    # =========================================================================
    # TAB 3: GESTIONE UTENTI
    # =========================================================================
    def _build_tab_users(self, tab: ctk.CTkFrame) -> None:
        toolbar = ctk.CTkFrame(tab, fg_color="transparent")
        toolbar.pack(fill="x", padx=15, pady=(10, 5))

        btn_add_u = ctk.CTkButton(
            toolbar,
            text="➕ Nuovo Utente",
            fg_color=COLOR_SUCCESS,
            hover_color=COLOR_SUCCESS_HOVER,
            width=130,
            command=self._show_add_user_dialog
        )
        btn_add_u.pack(side="left", padx=(0, 10))

        btn_role = ctk.CTkButton(
            toolbar,
            text="🔄 Cambia Ruolo",
            width=120,
            command=self._change_user_role
        )
        btn_role.pack(side="left", padx=(0, 10))

        btn_pwd = ctk.CTkButton(
            toolbar,
            text="🔑 Reset Password",
            width=130,
            command=self._reset_user_password
        )
        btn_pwd.pack(side="left", padx=(0, 10))

        btn_del_u = ctk.CTkButton(
            toolbar,
            text="🗑️ Elimina Utente",
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            width=130,
            command=self._delete_user
        )
        btn_del_u.pack(side="right")

        # Suggerimento ordinamento
        ctk.CTkLabel(
            tab,
            text="💡 Clicca sull'intestazione di qualsiasi colonna per ordinare la tabella (ascendente / discendente).",
            font=FONT_SMALL,
            text_color="gray"
        ).pack(anchor="w", padx=15, pady=(2, 0))

        # Treeview Utenti
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=(4, 10))

        self.users_col_titles = {
            "id": "ID",
            "username": "Nome Utente",
            "role": "Ruolo",
            "created": "Data Creazione",
            "last_login": "Ultimo Accesso",
        }
        cols = tuple(self.users_col_titles.keys())
        self.tree_users = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        for col, title in self.users_col_titles.items():
            self.tree_users.heading(
                col,
                text=title,
                command=lambda c=col: self._on_sort_column(self.tree_users, c, self.users_col_titles, self._users_sort)
            )

        self.tree_users.column("id", width=40, anchor="center")
        self.tree_users.column("username", width=160, anchor="w")
        self.tree_users.column("role", width=120, anchor="center")
        self.tree_users.column("created", width=160, anchor="center")
        self.tree_users.column("last_login", width=160, anchor="center")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_users.yview)
        self.tree_users.configure(yscrollcommand=sb.set)

        self.tree_users.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._refresh_users_list()

    def _refresh_users_list(self) -> None:
        for row in self.tree_users.get_children():
            self.tree_users.delete(row)
        users = self.db.get_all_users()
        for u in users:
            self.tree_users.insert("", "end", values=(
                u.id,
                u.username,
                u.role,
                u.created_at or "-",
                u.last_login or "-"
            ))
        if self._users_sort.get("col"):
            self._apply_tree_sort(self.tree_users, self._users_sort["col"], self.users_col_titles, self._users_sort["reverse"])

    def _show_add_user_dialog(self) -> None:
        dlg = ctk.CTkToplevel(self)
        dlg.title("Crea Nuovo Utente")
        dlg.geometry("360x320")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="Nome Utente:", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(20, 2))
        entry_u = ctk.CTkEntry(dlg, font=FONT_NORMAL)
        entry_u.pack(fill="x", padx=25, pady=(0, 10))

        ctk.CTkLabel(dlg, text="Password Iniziale:", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(5, 2))
        entry_p = ctk.CTkEntry(dlg, show="•", font=FONT_NORMAL)
        entry_p.pack(fill="x", padx=25, pady=(0, 10))

        ctk.CTkLabel(dlg, text="Ruolo:", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(5, 2))
        combo_role = ctk.CTkComboBox(dlg, values=["OPERATORE", "ADMIN"], font=FONT_NORMAL, state="readonly")
        combo_role.set("OPERATORE")
        combo_role.pack(fill="x", padx=25, pady=(0, 20))

        def save():
            u, p, r = entry_u.get(), entry_p.get(), combo_role.get()
            ok, msg = self.db.add_user(u, p, r)
            if ok:
                self._refresh_users_list()
                dlg.destroy()
            else:
                messagebox.showerror("Errore", msg, parent=dlg)

        btn_s = ctk.CTkButton(dlg, text="Crea Utente", fg_color=COLOR_SUCCESS, hover_color=COLOR_SUCCESS_HOVER, command=save)
        btn_s.pack(fill="x", padx=25)

    def _change_user_role(self) -> None:
        sel = self.tree_users.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un utente", parent=self)
            return
        vals = self.tree_users.item(sel[0])["values"]
        user_id, uname, cur_role = int(vals[0]), vals[1], vals[2]
        new_role = "OPERATORE" if cur_role == "ADMIN" else "ADMIN"

        if messagebox.askyesno("Cambio Ruolo", f"Modificare il ruolo di '{uname}' da {cur_role} a {new_role}?", parent=self):
            ok, msg = self.db.update_user_role(user_id, new_role)
            if ok:
                self._refresh_users_list()
            else:
                messagebox.showerror("Errore", msg, parent=self)

    def _reset_user_password(self) -> None:
        sel = self.tree_users.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un utente", parent=self)
            return
        vals = self.tree_users.item(sel[0])["values"]
        user_id, uname = int(vals[0]), vals[1]

        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Reset Password - {uname}")
        dlg.geometry("340x200")
        dlg.transient(self)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text=f"Nuova password per {uname}:", font=FONT_SMALL).pack(anchor="w", padx=25, pady=(20, 2))
        entry_p = ctk.CTkEntry(dlg, show="•", font=FONT_NORMAL)
        entry_p.pack(fill="x", padx=25, pady=(0, 20))

        def save():
            p = entry_p.get()
            if not p:
                messagebox.showerror("Errore", "La password non può essere vuota", parent=dlg)
                return
            ok, msg = self.db.update_user_password(user_id, p)
            if ok:
                messagebox.showinfo("Successo", f"Password di '{uname}' aggiornata", parent=self)
                dlg.destroy()
            else:
                messagebox.showerror("Errore", msg, parent=dlg)

        ctk.CTkButton(dlg, text="Conferma Reset", fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, command=save).pack(fill="x", padx=25)

    def _delete_user(self) -> None:
        sel = self.tree_users.selection()
        if not sel:
            messagebox.showwarning("Attenzione", "Seleziona un utente da eliminare", parent=self)
            return
        vals = self.tree_users.item(sel[0])["values"]
        user_id, uname = int(vals[0]), vals[1]
        cur_u = SessionManager.get_user()
        cur_id = cur_u.id if cur_u and cur_u.id is not None else -1

        if messagebox.askyesno("Conferma Eliminazione", f"Sei sicuro di voler eliminare l'utente '{uname}'?", parent=self):
            ok, msg = self.db.delete_user(user_id, cur_id)
            if ok:
                self._refresh_users_list()
            else:
                messagebox.showerror("Errore", msg, parent=self)

    # =========================================================================
    # TAB 4: CODICI LABORATORIO
    # =========================================================================
    def _build_tab_labs(self, tab: ctk.CTkFrame) -> None:
        config = self.db.get_config()

        ctk.CTkLabel(
            tab,
            text="Prefissi identificativi dei laboratori abilitati (2 caratteri ciascuno, separati da virgola):",
            font=FONT_NORMAL,
            text_color="gray"
        ).pack(anchor="w", padx=25, pady=(20, 10))

        self.entry_labs = ctk.CTkEntry(tab, font=FONT_NORMAL, width=500)
        self.entry_labs.insert(0, config.allowed_labs_str)
        self.entry_labs.pack(anchor="w", padx=25, pady=(0, 20))

        ctk.CTkLabel(
            tab,
            text="Esempio predefinito: BG, MI, BS, RL, VP, MN, MB\n(Bergamo, Milano, Brescia, Preaccettato, Valpadana, Montagna, MonzaBrianza)",
            font=FONT_SMALL,
            text_color="gray"
        ).pack(anchor="w", padx=25, pady=(0, 25))

        btn_save_labs = ctk.CTkButton(
            tab,
            text="💾 Salva Codici Laboratorio",
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._save_labs
        )
        btn_save_labs.pack(anchor="w", padx=25)

    def _save_labs(self) -> None:
        raw_labs = self.entry_labs.get().strip().upper()
        if not raw_labs:
            messagebox.showerror("Errore", "Inserisci almeno un codice laboratorio valido", parent=self)
            return
        self.db.save_config_value("allowed_labs", raw_labs, "Codici identificativi laboratori abilitati")
        messagebox.showinfo("Successo", "Codici laboratorio aggiornati con successo", parent=self)

    # =========================================================================
    # TAB 5: MANUTENZIONE DATI (PULIZIA CAMPIONI ESPORTATI)
    # =========================================================================
    def _build_tab_maintenance(self, tab: ctk.CTkFrame) -> None:
        """Costruisce il pannello per l'eliminazione dei campioni esportati da una data specificata."""
        # Descrizione
        lbl_desc = ctk.CTkLabel(
            tab,
            text="Permette agli utenti Amministratori di eliminare dal database locale tutti i campioni che risultano\n"
                 "già esportati per il LIS (stato 'ESPORTATO') a partire da una data specificata.\n"
                 "Verranno eliminati anche i relativi parametri analitici, mentre i file archiviati su disco saranno preservati.",
            font=FONT_NORMAL,
            text_color="gray",
            justify="left"
        )
        lbl_desc.pack(anchor="w", padx=25, pady=(15, 10))

        # Card Filtro Data
        card_filter = ctk.CTkFrame(tab, corner_radius=10)
        card_filter.pack(fill="x", padx=25, pady=(0, 10))

        row_date = ctk.CTkFrame(card_filter, fg_color="transparent")
        row_date.pack(fill="x", padx=15, pady=(12, 6))

        ctk.CTkLabel(
            row_date,
            text="📅 Elimina campioni esportati a partire dal (>=):",
            font=FONT_SECTION
        ).pack(side="left", padx=(0, 10))

        default_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        self.entry_maint_date = ctk.CTkEntry(
            row_date,
            width=130,
            height=32,
            font=FONT_NORMAL,
            placeholder_text="AAAA-MM-GG"
        )
        self.entry_maint_date.insert(0, default_date)
        self.entry_maint_date.pack(side="left", padx=(0, 10))

        btn_preview = ctk.CTkButton(
            row_date,
            text="🔍 Mostra Anteprima",
            width=145,
            height=32,
            font=FONT_NORMAL,
            fg_color=COLOR_PRIMARY,
            hover_color=COLOR_PRIMARY_HOVER,
            command=self._refresh_maint_preview
        )
        btn_preview.pack(side="left", padx=5)

        # Riga scorciatoie rapide per la data
        row_presets = ctk.CTkFrame(card_filter, fg_color="transparent")
        row_presets.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(
            row_presets,
            text="Seleziona data rapida:",
            font=FONT_SMALL,
            text_color="gray"
        ).pack(side="left", padx=(0, 8))

        def _set_date(d_str: str) -> None:
            self.entry_maint_date.delete(0, "end")
            self.entry_maint_date.insert(0, d_str)
            self._refresh_maint_preview()

        now = datetime.now()
        presets = [
            ("Oggi", now.strftime("%Y-%m-%d")),
            ("Inizio Mese", now.replace(day=1).strftime("%Y-%m-%d")),
            ("30 Giorni Fa", (now - timedelta(days=30)).strftime("%Y-%m-%d")),
            ("Inizio Anno", datetime(now.year, 1, 1).strftime("%Y-%m-%d")),
        ]

        for label, val in presets:
            btn_p = ctk.CTkButton(
                row_presets,
                text=label,
                width=85,
                height=24,
                font=FONT_SMALL,
                fg_color="transparent",
                border_width=1,
                text_color=("black", "white"),
                command=lambda v=val: _set_date(v)
            )
            btn_p.pack(side="left", padx=3)

        # Tabella Anteprima
        preview_container = ctk.CTkFrame(tab, fg_color="transparent")
        preview_container.pack(fill="both", expand=True, padx=25, pady=(0, 10))

        hdr_row = ctk.CTkFrame(preview_container, fg_color="transparent")
        hdr_row.pack(fill="x", pady=(0, 5))

        self.lbl_maint_count = ctk.CTkLabel(
            hdr_row,
            text="Campioni esportati trovati: 0",
            font=FONT_SECTION
        )
        self.lbl_maint_count.pack(side="left")

        tree_box = ctk.CTkFrame(preview_container, fg_color="transparent")
        tree_box.pack(fill="both", expand=True)

        cols = ("code", "lab", "acc", "conf", "samp", "exported_at", "filename", "params")
        self.tree_maint = ttk.Treeview(tree_box, columns=cols, show="headings", selectmode="browse", height=7)

        self.tree_maint.heading("code", text="Codice Campione")
        self.tree_maint.heading("lab", text="Lab")
        self.tree_maint.heading("acc", text="Accettazione")
        self.tree_maint.heading("conf", text="Conf.")
        self.tree_maint.heading("samp", text="Camp.")
        self.tree_maint.heading("exported_at", text="Data Esportazione")
        self.tree_maint.heading("filename", text="File Esportato")
        self.tree_maint.heading("params", text="N. Parametri")

        self.tree_maint.column("code", width=160, anchor="w")
        self.tree_maint.column("lab", width=45, anchor="center")
        self.tree_maint.column("acc", width=85, anchor="center")
        self.tree_maint.column("conf", width=45, anchor="center")
        self.tree_maint.column("samp", width=45, anchor="center")
        self.tree_maint.column("exported_at", width=130, anchor="center")
        self.tree_maint.column("filename", width=150, anchor="w")
        self.tree_maint.column("params", width=75, anchor="center")

        sb_y = ttk.Scrollbar(tree_box, orient="vertical", command=self.tree_maint.yview)
        self.tree_maint.configure(yscrollcommand=sb_y.set)
        self.tree_maint.pack(side="left", fill="both", expand=True)
        sb_y.pack(side="right", fill="y")

        # Bottom Action Bar
        bottom_bar = ctk.CTkFrame(tab, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=25, pady=(0, 15))

        lbl_warn = ctk.CTkLabel(
            bottom_bar,
            text="⚠️ L'eliminazione è irreversibile per i record del database.",
            font=FONT_SMALL,
            text_color="gray"
        )
        lbl_warn.pack(side="left")

        self.btn_execute_delete = ctk.CTkButton(
            bottom_bar,
            text="🗑️ Elimina Campioni Esportati",
            font=FONT_SUBTITLE,
            fg_color=COLOR_DANGER,
            hover_color=COLOR_DANGER_HOVER,
            height=36,
            command=self._execute_maint_delete
        )
        self.btn_execute_delete.pack(side="right")

        # Carica anteprima iniziale
        self._refresh_maint_preview()

    def _refresh_maint_preview(self) -> None:
        """Aggiorna l'anteprima dei campioni esportati corrispondenti alla data impostata."""
        raw_date = self.entry_maint_date.get().strip()
        if not raw_date:
            return

        try:
            samples = self.db.get_exported_samples_from_date(raw_date)
        except ValueError as e:
            messagebox.showerror("Data Non Valida", str(e), parent=self)
            return

        self._maint_samples_cache = samples

        for item in self.tree_maint.get_children():
            self.tree_maint.delete(item)

        for s in samples:
            self.tree_maint.insert(
                "",
                "end",
                values=(
                    s.sample_code,
                    s.lab_code,
                    s.acceptance,
                    s.conferment,
                    s.sample_number,
                    s.exported_at or s.imported_at or "-",
                    s.export_filename or "-",
                    s.results_count,
                )
            )

        self.lbl_maint_count.configure(
            text=f"Campioni esportati trovati: {len(samples)} (a partire dal {raw_date})"
        )

    def _execute_maint_delete(self) -> None:
        """Esegue l'eliminazione dei campioni esportati previa conferma esplicita dell'utente."""
        raw_date = self.entry_maint_date.get().strip()
        if not raw_date:
            messagebox.showwarning("Attenzione", "Specificare una data di riferimento valida.", parent=self)
            return

        try:
            samples = self.db.get_exported_samples_from_date(raw_date)
        except ValueError as e:
            messagebox.showerror("Data Non Valida", str(e), parent=self)
            return

        count = len(samples)
        if count == 0:
            messagebox.showinfo(
                "Nessun Campione",
                f"Nessun campione esportato trovato a partire dalla data {raw_date}.\nNessuna operazione necessaria.",
                parent=self
            )
            return

        confirm = messagebox.askyesno(
            "Conferma Eliminazione Definitiva",
            f"Sei sicuro di voler ELIMINARE DEFINITIVAMENTE {count} campioni esportati a partire dal {raw_date}?\n\n"
            f"• Verranno rimossi i record dei campioni e tutti i relativi risultati analitici dal database locale.\n"
            f"• I file archiviati nella cartella 'archiviati' e i CSV esportati non verranno eliminati.\n\n"
            f"Questa operazione NON può essere annullata. Procedere con l'eliminazione?",
            icon="warning",
            parent=self
        )

        if not confirm:
            return

        cur_user = SessionManager.get_user()
        if not cur_user:
            messagebox.showerror("Errore", "Nessuna sessione utente attiva.", parent=self)
            return

        ok, msg, deleted_count = self.db.delete_exported_samples_from_date(raw_date, cur_user)
        if ok:
            messagebox.showinfo("Eliminazione Completata", msg, parent=self)
            self._refresh_maint_preview()
            if self.on_config_changed:
                self.on_config_changed()
        else:
            messagebox.showerror("Errore", msg, parent=self)

    # =========================================================================
    # ORDINAMENTO GRIGLIE TREEVIEW
    # =========================================================================
    def _on_sort_column(
        self,
        tree: ttk.Treeview,
        col: str,
        col_titles: dict[str, str],
        sort_state: dict[str, Any]
    ) -> None:
        """Gestisce il click dell'utente sull'intestazione di colonna per ordinare la tabella.

        Alterna la direzione di ordinamento (ascendente/discendente) se viene cliccata
        la stessa colonna, oppure imposta l'ordinamento ascendente predefinito su una nuova colonna.

        Args:
            tree: L'istanza ttk.Treeview da ordinare.
            col: L'identificatore della colonna cliccata.
            col_titles: Mappa degli identificatori colonna con le etichette originali.
            sort_state: Dizionario che memorizza lo stato corrente {'col': str, 'reverse': bool}.
        """
        if sort_state.get("col") == col:
            sort_state["reverse"] = not sort_state.get("reverse", False)
        else:
            sort_state["col"] = col
            sort_state["reverse"] = False

        self._apply_tree_sort(tree, col, col_titles, sort_state["reverse"])

    def _apply_tree_sort(
        self,
        tree: ttk.Treeview,
        col: str,
        col_titles: dict[str, str],
        reverse: bool
    ) -> None:
        """Riordina le righe della Treeview in base ai valori della colonna specificata.

        Supporta ordinamento numerico (ID), temporale/cronologico e testuale alfabetico
        senza distinzione tra maiuscole e minuscole. Gli elementi vuoti o segnaposto '-'
        vengono posizionati ordinatamente in coda.

        Args:
            tree: L'istanza ttk.Treeview da riordinare.
            col: L'identificatore della colonna di riferimento.
            col_titles: Mappa dei titoli originali per l'aggiornamento dell'indicatore freccia (▲/▼).
            reverse: True per ordinamento discendente, False per ascendente.
        """
        items = tree.get_children("")
        if not items:
            return

        valid_items: list[tuple[tuple[int, Any], str]] = []
        empty_items: list[str] = []

        for item_id in items:
            val = tree.set(item_id, col)
            if val is None or str(val).strip() in ("", "-"):
                empty_items.append(item_id)
            else:
                s = str(val).strip()
                # Riconoscimento automatico del tipo per ordinamento naturale
                try:
                    # Intero (es. ID)
                    k: tuple[int, Any] = (0, int(s))
                except ValueError:
                    try:
                        # Decimale
                        k = (0, float(s.replace(",", ".")))
                    except ValueError:
                        # Stringa testuale o data ISO (es. "2026-09-07 10:00:00")
                        k = (1, s.lower())
                valid_items.append((k, item_id))

        valid_items.sort(key=lambda x: x[0], reverse=reverse)
        ordered_ids = [item_id for _, item_id in valid_items] + empty_items

        # Riposiziona gli elementi visivamente nella tabella
        for index, item_id in enumerate(ordered_ids):
            tree.move(item_id, "", index)

        # Aggiorna le etichette con indicatori grafici di ordinamento
        for c, title in col_titles.items():
            if c == col:
                arrow = " ▲" if not reverse else " ▼"
                tree.heading(c, text=f"{title}{arrow}")
            else:
                tree.heading(c, text=title)
