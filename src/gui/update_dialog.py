# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Controllo asincrono delle Release e strumenti amministrativi di backup."""

from __future__ import annotations

from pathlib import Path
import queue
import json
import subprocess
import sys
import threading
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

from src import __version__
from src.auth import SessionManager
from src.backup import dated_backup
from src.config import BASE_DIR
from src.update_service import Release, UpdateError, check_release, stage_release


class UpdateController:
    """Esegue I/O fuori da Tk e consegna i risultati nel thread grafico."""

    def __init__(self, window: ctk.CTk):
        self.window = window
        self.release: Release | None = None
        self.error = ""
        self.checked = False
        self.busy = False
        self.operation_busy = False
        self.notified = False
        self.events: queue.Queue = queue.Queue()
        self.listeners: list[Callable[[], None]] = []
        self.timer = window.after(100, self._poll)
        self.notice_checked = False

    def check(self) -> None:
        """Accoda una sola verifica per volta, richiamabile anche dal pannello."""
        if self.busy:
            return
        self.busy = True
        self._notify_listeners()

        def worker() -> None:
            try:
                self.events.put((check_release(), ""))
            except Exception as exc:
                self.events.put((None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _notify_listeners(self) -> None:
        """Aggiorna solo finestre ancora registrate dal relativo dialogo."""
        for callback in self.listeners[:]:
            callback()

    def _poll(self) -> None:
        """Tutte le operazioni Tk, inclusi i popup, rimangono nel main thread."""
        if not self.notice_checked:
            self.notice_checked = True
            notice = BASE_DIR / ".updates/last-result.json"
            if notice.exists():
                try:
                    result = json.loads(notice.read_text(encoding="utf-8"))
                    if not result.get("reported"):
                        messagebox.showinfo("Esito aggiornamento", result["message"], parent=self.window)
                        result["reported"] = True
                        from update_runner import atomic_json
                        atomic_json(notice, result)
                except (OSError, ValueError, KeyError):
                    pass
        try:
            self.release, self.error = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.checked = True
            self._notify_listeners()
            if self.release and not self.notified:
                self.notified = True
                messagebox.showwarning(
                    "Aggiornamento disponibile",
                    f"È disponibile Strumenti LYSA {self.release.version}.\n\n"
                    f"{self.release.database_message}\n\n{self.release.notes[:1800]}\n\n"
                    "Per installare: amministratore → Impostazioni → Aggiornamenti e backup.\n"
                    "Se sei un operatore, contatta l'amministratore.", parent=self.window)
        self.timer = self.window.after(100, self._poll)

    def close(self) -> None:
        """Evita callback Tk pendenti dopo chiusura o riavvio dell'app."""
        self.window.after_cancel(self.timer)
        self.listeners.clear()


def require_admin() -> None:
    """Ricontrolla il ruolo a ogni azione sensibile, oltre al filtro della GUI."""
    if not SessionManager.is_admin():
        raise PermissionError("Operazione riservata agli amministratori")


class UpdateDialog(ctk.CTkToplevel):
    """Pannello amministrativo con verifica, installazione e copia completa DB."""

    def __init__(self, parent, db, controller: UpdateController):
        require_admin()
        super().__init__(parent)
        self.db, self.controller = db, controller
        self.title("Aggiornamenti e backup")
        self.geometry("760x600")
        self.transient(parent)
        self.grab_set()
        self.pending = False
        self.events: queue.Queue = queue.Queue()
        ctk.CTkLabel(self, text=f"Versione installata: {__version__}", font=("Arial", 19, "bold")).pack(pady=15)
        self.status = ctk.CTkLabel(self, text="", wraplength=710)
        self.status.pack(padx=15, pady=5)
        self.notes = ctk.CTkTextbox(self, wrap="word")
        self.notes.pack(fill="both", expand=True, padx=20, pady=10)
        actions = ctk.CTkFrame(self)
        actions.pack(fill="x", padx=20, pady=10)
        self.check_button = ctk.CTkButton(actions, text="Verifica aggiornamenti", command=self._check)
        self.check_button.pack(side="left", padx=5, pady=10)
        self.install_button = ctk.CTkButton(actions, text="Installa e riavvia", command=self._install)
        self.install_button.pack(side="left", padx=5)
        self.backup_button = ctk.CTkButton(actions, text="Crea copia database", command=self._backup)
        self.backup_button.pack(side="left", padx=5)
        ctk.CTkLabel(self, text="Le copie restano sul PC e includono tutti i dati. Nessun caricamento su GitHub.",
                     wraplength=710).pack(padx=15, pady=(0, 12))
        self.controller.listeners.append(self.refresh)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.timer = self.after(100, self._poll)
        self.refresh()

    def refresh(self) -> None:
        """Mostra anche errori di rete che il controllo all'avvio lascia silenziosi."""
        controller = self.controller
        if controller.busy:
            status = "Verifica GitHub in corso…"
        elif controller.error:
            status = controller.error
        elif controller.release:
            status = f"Disponibile: {controller.release.version}\n{controller.release.database_message}"
        else:
            status = "Nessuna nuova versione disponibile." if controller.checked else "Verifica non ancora eseguita."
        self.status.configure(text=status)
        self.notes.configure(state="normal")
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", controller.release.notes if controller.release else "")
        self.notes.configure(state="disabled")
        self.check_button.configure(state="disabled" if controller.busy or self.pending else "normal")
        self.backup_button.configure(state="disabled" if self.pending else "normal")
        self.install_button.configure(state="normal" if controller.release and not self.pending and not controller.busy else "disabled")

    def _check(self) -> None:
        """Verifica manuale consentita soltanto alla sessione amministrativa."""
        require_admin()
        self.controller.check()

    def _run(self, function: Callable) -> None:
        """Esegue download e backup con un solo lavoro amministrativo per volta."""
        self.pending = True
        self.controller.operation_busy = True
        self.refresh()

        def worker() -> None:
            try:
                self.events.put((True, function()))
            except Exception as exc:
                self.events.put((False, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _backup(self) -> None:
        """Chiede una cartella e salva una copia completa con nome univoco."""
        require_admin()
        directory = filedialog.askdirectory(title="Destinazione copia completa database", parent=self)
        if directory:
            self._run(lambda: ("backup", dated_backup(self.db.db_path, Path(directory))))

    def _install(self) -> None:
        """Raccoglie il consenso, separando l'eventuale perdita dello storico."""
        require_admin()
        release = self.controller.release
        if not release:
            return
        if (BASE_DIR / ".git").exists():
            messagebox.showinfo("Copia di sviluppo", "Usare sync.bat o il flusso Git del progetto.\nControllo versioni e backup restano disponibili.", parent=self)
            return
        reset = release.manifest["database"]["mode"] == "reset"
        if reset and not messagebox.askyesno(
                "Conferma perdita dati", release.database_message +
                "\n\nVerranno salvati il database completo e i canali già codificati. "
                "Le transcodifiche saranno recuperate automaticamente; il TXT sarà disponibile "
                "per l'importazione in Impostazioni → Transcodifiche LIS.\n\nConfermi il database nuovo?", parent=self):
            return
        if not messagebox.askyesno("Installa aggiornamento", "L'app verrà chiusa e riavviata. "
                                  "Programma, ambiente e database saranno conservati per il ripristino.\n"
                                  "Backup e canali saranno in .updates nella cartella del programma.\n\nProcedere?", parent=self):
            return
        with self.db.get_connection() as conn:
            schema = conn.execute("PRAGMA user_version").fetchone()[0]
        self._run(lambda: ("install", stage_release(release, BASE_DIR, schema, reset_confirmed=reset)))

    def _poll(self) -> None:
        """Consegna risultati e avvia il runner solo dal thread grafico."""
        try:
            ok, result = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.pending = False
            self.controller.operation_busy = False
            self.refresh()
            if not ok:
                messagebox.showerror("Operazione non completata", result, parent=self)
            elif result[0] == "backup":
                messagebox.showinfo("Copia completata", f"Copia completa verificata:\n{result[1]}", parent=self)
            else:
                require_admin()
                job = result[1]
                if not messagebox.askyesno("Pacchetto verificato", f"Il programma verrà ora chiuso.\n"
                                          f"Backup completo e transcodifiche saranno salvati in:\n{job}\n\nInstalla e riavvia?", parent=self):
                    self.timer = self.after(100, self._poll)
                    return
                # Il runner deve essere indipendente dalla .venv che aggiornerà.
                base_python = getattr(sys, "_base_executable", sys.executable)
                try:
                    if Path(base_python).resolve().is_relative_to((BASE_DIR / ".venv").resolve()):
                        raise OSError("Runtime Python base non disponibile")
                    subprocess.Popen([base_python, str(job / "runner.py"), str(BASE_DIR), str(job)], cwd=BASE_DIR,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                except OSError as exc:
                    messagebox.showerror("Installazione non avviata", str(exc), parent=self)
                    self.timer = self.after(100, self._poll)
                    return
                self.controller.window.destroy()
                return
        self.timer = self.after(100, self._poll)

    def _close(self) -> None:
        """Non interrompe una copia in corso e restituisce il grab alle impostazioni."""
        if self.pending:
            messagebox.showinfo("Operazione in corso", "Attendere il completamento dell'operazione.", parent=self)
            return
        self.after_cancel(self.timer)
        self.controller.listeners.remove(self.refresh)
        parent = self.master
        self.destroy()
        if parent.winfo_exists():
            parent.grab_set()
