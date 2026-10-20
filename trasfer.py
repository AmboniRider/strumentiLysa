# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Crea un pacchetto Windows installabile, senza storico dei campioni.

Il motore usa solo la libreria standard ed è separato dalla GUI: esportare non
deve inizializzare il database operativo né importare l'applicazione principale.
"""

from __future__ import annotations

import os
from contextlib import closing
from pathlib import Path
import queue
import sqlite3
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parent
UV_VERSION = "0.12.14"
PYTHON_VERSION = "3.12.13"
# Un elenco positivo evita di esportare nuovi file riservati aggiunti al progetto.
RUNTIME_FILES = (
    "app.py", "driver.py", "pyproject.toml", "uv.lock", "LICENSE", "strumenti.ico",
    "update_runner.py", "maintenance.py",
    "manuale.md", "progetto.md", "transfer.md", "UPDATES.md", "LEGAL.md",
    "src/__init__.py", "src/auth.py", "src/config.py", "src/database.py",
    "src/exporter.py", "src/importer_service.py", "src/models.py", "src/validator.py",
    "src/gui/__init__.py", "src/gui/app_window.py", "src/gui/help_dialog.py",
    "src/gui/login_view.py", "src/gui/master_detail.py", "src/gui/password_dialog.py",
    "src/gui/settings_dialog.py", "src/gui/theme.py",
    "src/backup.py", "src/update_service.py", "src/gui/update_dialog.py", "src/gui/license_dialog.py",
    "driver_implementati/README.md", "driver_implementati/dionex_ic.md",
    "driver_implementati/mettler_toledo.md", "driver_implementati/spettrofotometro_uv_vis.md",
    "driver_implementati/agilent_5977c.md",
)
PATH_KEYS = ("path_input", "path_archive", "path_error", "path_export")
ProgressCallback = Callable[[int, str], None]


class TransferError(Exception):
    """Errore operativo da presentare all'utente senza contenuti del database."""


def init_terminal(title: str) -> None:
    """Imposta titolo console e banner ANSI, tollerando console non disponibili."""
    if sys.stdout is None:
        return
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    sys.stdout.write(f"\033]0;{title}\007")
    box = "═" * (len(title) + 6)
    print(f"\n\033[93m╔{box}╗\n║   \033[96m{title}\033[93m   ║\n╚{box}╝\033[0m\n")


def batch_environment() -> str:
    """Configurazione comune: tutti gli strumenti restano nella cartella estratta."""
    return r'''@echo off
setlocal
chcp 65001 > nul
pushd "%~dp0"
if errorlevel 1 exit /b 1
set "UV_PROJECT_ENVIRONMENT=%~dp0.venv"
set "VIRTUAL_ENV="
set "UV_PYTHON_INSTALL_DIR=%~dp0.runtime\python"
set "UV_CACHE_DIR=%~dp0.uv-cache"
set "UV_PYTHON_INSTALL_BIN=0"
set "UV_PYTHON_INSTALL_REGISTRY=0"
'''


def installer_batch() -> str:
    """Genera l'installazione ripetibile senza Python, Git o uv preinstallati."""
    return batch_environment() + fr'''title INSTALLAZIONE STRUMENTI - LIS
echo =======================================================
echo          INSTALLAZIONE STRUMENTI - LIS
echo =======================================================
if /i "%PROCESSOR_ARCHITECTURE%"=="AMD64" goto architecture_ok
if /i "%PROCESSOR_ARCHITEW6432%"=="AMD64" goto architecture_ok
echo Questa installazione richiede Windows x64.
goto failed
:architecture_ok
set "UV_UNMANAGED_INSTALL=%~dp0.tools"
if exist ".tools\uv.exe" goto sync
echo Download di uv {UV_VERSION}. E' necessaria una connessione Internet.
rem Usa i moduli Windows: evita conflitti con PSModulePath ereditato da PowerShell 7.
set "PSModulePath=%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules"
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; irm https://astral.sh/uv/{UV_VERSION}/install.ps1 | iex"
if errorlevel 1 goto failed
if not exist ".tools\uv.exe" goto failed
:sync
".tools\uv.exe" python install {PYTHON_VERSION} --no-bin --no-registry
if errorlevel 1 goto failed
".tools\uv.exe" sync --locked --no-dev --no-install-project --python {PYTHON_VERSION} --managed-python
if errorlevel 1 goto failed
".tools\uv.exe" run --no-sync --offline python -c "import tkinter, tkinter.ttk, customtkinter, PIL; r=tkinter.Tk(); r.withdraw(); r.destroy(); print('Interfaccia grafica e dipendenze verificate.')"
if errorlevel 1 goto failed
echo Installazione completata. Avviare strumenti.bat.
popd
pause
exit /b 0
:failed
echo Installazione non completata. Consultare transfer.md e riprovare installa.bat.
popd
pause
exit /b 1
'''


def launcher_batch() -> str:
    """Genera l'avvio offline, che non sincronizza o modifica le dipendenze."""
    return batch_environment() + r'''title STRUMENTI DI LABORATORIO - LIS
echo =======================================================
echo          STRUMENTI DI LABORATORIO - LIS
echo =======================================================
if not exist ".tools\uv.exe" goto missing
rem Recupero con Python base: funziona anche con un ambiente virtuale interrotto.
for /f "delims=" %%P in ('".tools\uv.exe" python find --managed-python ''' + PYTHON_VERSION + r'''') do set "RECOVERY_PYTHON=%%P"
if not defined RECOVERY_PYTHON goto missing
"%RECOVERY_PYTHON%" update_runner.py recover-only
if errorlevel 1 goto failed
if not exist ".venv\Scripts\python.exe" goto missing
".tools\uv.exe" run --no-sync --offline python app.py
if errorlevel 1 goto failed
popd
exit /b 0
:missing
echo Eseguire prima installa.bat con una connessione Internet disponibile.
goto failed
:failed
echo Avvio non riuscito. Consultare transfer.md.
popd
pause
exit /b 1
'''


def sanitized_database(source: Path, target: Path) -> None:
    """Copia SQLite e rimuove lo storico dalla sola copia destinata allo ZIP.

    Parametri: source è il database esistente; target è un nuovo file temporaneo.
    Non restituisce valori. Solleva TransferError se backup o controlli falliscono.
    La Backup API include le transazioni confermate nel WAL. VACUUM ricostruisce
    le pagine, evitando residui dei dati cancellati nel file distribuito.
    """
    if not source.is_file():
        raise TransferError("Database data/strumenti.db mancante.")
    deadline = time.monotonic() + 30

    def check_timeout(status: int, remaining: int, total: int) -> None:
        """Limita l'attesa anche quando il database rimane occupato."""
        if time.monotonic() > deadline:
            raise TransferError("Database occupato: chiudere l'applicazione e riprovare.")

    try:
        # mode=ro impedisce la creazione o la modifica dei record sul sorgente.
        with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original:
            copied = sqlite3.connect(target)
            try:
                original.backup(copied, pages=128, progress=check_timeout, sleep=0.1)
                expected = {"users", "configurations", "transcodings", "samples", "sample_results", "audit_logs"}
                tables = {row[0] for row in copied.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                if tables != expected:
                    # Fallire su schemi futuri evita di includere nuove tabelle
                    # contenenti campioni senza una revisione delle esclusioni.
                    raise TransferError("Schema database non compatibile con il trasferimento.")
                if copied.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise TransferError("Il database sorgente non supera il controllo di integrità.")
                copied.execute("PRAGMA journal_mode=DELETE")
                copied.execute("PRAGMA foreign_keys=ON")
                copied.execute("PRAGMA secure_delete=ON")
                with copied:
                    for table in ("sample_results", "samples", "audit_logs"):
                        copied.execute(f"DELETE FROM {table}")
                    copied.execute("DELETE FROM sqlite_sequence WHERE name IN ('sample_results', 'samples', 'audit_logs')")
                    copied.executemany("DELETE FROM configurations WHERE key=?", [(key,) for key in PATH_KEYS])
                copied.execute("VACUUM")
                if copied.execute("PRAGMA integrity_check").fetchall() != [("ok",)] or copied.execute("PRAGMA foreign_key_check").fetchall():
                    raise TransferError("La copia del database non supera i controlli di integrità.")
            finally:
                copied.close()
    except sqlite3.Error as exc:
        # Non riportiamo query, record o credenziali nei messaggi della GUI.
        raise TransferError("Impossibile preparare il database: file non valido o non accessibile.") from exc


def create_transfer(destination: Path, source_root: Path = PROJECT_ROOT,
                    progress: ProgressCallback | None = None) -> Path:
    """Salva uno ZIP verificato nella destinazione e ne restituisce il percorso.

    source_root identifica il progetto; progress riceve percentuale e descrizione.
    Tutte le scritture temporanee sono sotto destination. Errori di I/O vengono
    propagati al chiamante; il sorgente e gli ZIP preesistenti restano intatti.
    """
    destination = destination.resolve()
    source_root = source_root.resolve()
    if not destination.is_dir():
        raise TransferError("Selezionare una cartella di destinazione esistente.")
    for relative in (*RUNTIME_FILES, "data/strumenti.db"):
        path = source_root / relative
        if not path.is_file() or not path.resolve().is_relative_to(source_root):
            raise TransferError(f"File obbligatorio mancante o esterno al progetto: {relative}")
    report = progress or (lambda percent, description: None)
    name = f"strumenti_transfer_{datetime.now():%Y%m%d_%H%M%S_%f}.zip"
    final_path = destination / name
    # La destinazione può essere anche il progetto: l'elenco esplicito impedisce
    # di includere lo ZIP in costruzione o i temporanei nel pacchetto stesso.
    with tempfile.TemporaryDirectory(prefix=".transfer-", dir=destination) as temporary:
        staging = Path(temporary)
        report(0, "Preparazione del database senza campioni e audit...")
        database = staging / "strumenti.db"
        sanitized_database(source_root / "data/strumenti.db", database)
        archive_path = staging / "pacchetto.zip"
        with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as archive:
            for index, relative in enumerate(RUNTIME_FILES, 1):
                archive.write(source_root / relative, "strumenti/" + relative)
                report(10 + index * 70 // len(RUNTIME_FILES), f"Compressione: {relative}")
            archive.write(database, "strumenti/data/strumenti.db")
            for relative, content in (("installa.bat", installer_batch()), ("strumenti.bat", launcher_batch())):
                archive.writestr("strumenti/" + relative, content.replace("\n", "\r\n").encode("utf-8"))
        report(90, "Verifica dell'archivio...")
        with ZipFile(archive_path) as archive:
            if archive.testzip() is not None:
                raise TransferError("Verifica ZIP fallita: archivio non pubblicato.")
        # Su Windows rename è atomico e rifiuta una destinazione già esistente.
        # Anche negli altri OS il controllo impedisce sovrascritture ordinarie.
        if final_path.exists():
            raise TransferError("Archivio già esistente: riprovare per generare un nuovo nome.")
        archive_path.rename(final_path)
    report(100, "Archivio pronto.")
    return final_path


class TransferWindow(tk.Tk):
    """Finestra ttk con un solo worker; tutte le operazioni Tk restano sul main thread."""

    def __init__(self) -> None:
        """Crea controlli, coda eventi e gestione della chiusura."""
        super().__init__()
        self.title("Trasferimento Strumenti - LIS")
        self.geometry("680x340")
        self.minsize(600, 320)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False
        self.destination = tk.StringVar()
        self.status = tk.StringVar(value="Seleziona la cartella in cui salvare lo ZIP.")
        self.columnconfigure(0, weight=1)
        body = ttk.Frame(self, padding=20)
        body.grid(sticky="nsew")
        body.columnconfigure(0, weight=1)
        ttk.Label(body, text="Trasferimento Strumenti - LIS", font=("Segoe UI", 16, "bold")).grid(sticky="w", columnspan=2)
        ttk.Label(body, text="Windows x64 • Installazione con Internet\nInclude utenti, impostazioni e transcodifiche.\nEsclude campioni, risultati, audit e file operativi.").grid(sticky="w", columnspan=2, pady=12)
        self.entry = ttk.Entry(body, textvariable=self.destination)
        self.entry.grid(row=2, column=0, sticky="ew", padx=(0, 8))
        self.browse = ttk.Button(body, text="Sfoglia...", command=self.choose_destination)
        self.browse.grid(row=2, column=1)
        self.create = ttk.Button(body, text="Crea ZIP", command=self.start_transfer)
        self.create.grid(row=3, column=0, sticky="w", pady=15)
        self.bar = ttk.Progressbar(body, maximum=100)
        self.bar.grid(row=4, column=0, columnspan=2, sticky="ew")
        ttk.Label(body, textvariable=self.status, wraplength=600).grid(row=5, column=0, columnspan=2, sticky="w", pady=10)
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.after(100, self.poll_events)

    def choose_destination(self) -> None:
        """Seleziona la cartella tramite il dialogo nativo."""
        selected = filedialog.askdirectory(parent=self, title="Cartella in cui salvare lo ZIP")
        if selected:
            self.destination.set(selected)

    def start_transfer(self) -> None:
        """Valida la selezione e avvia il worker senza accedere a Tk dal thread."""
        if self.busy:
            return
        selected = self.destination.get().strip()
        if not selected or not Path(selected).is_dir():
            messagebox.showerror("Destinazione", "Selezionare una cartella esistente.", parent=self)
            return
        self.busy = True
        self.bar["value"] = 0
        for control in (self.entry, self.browse, self.create):
            control.configure(state="disabled")
        threading.Thread(target=self.run_transfer, args=(Path(selected),), daemon=False).start()

    def run_transfer(self, destination: Path) -> None:
        """Esegue il lavoro e invia esclusivamente messaggi alla coda."""
        try:
            result = create_transfer(destination, progress=lambda value, label: self.events.put(("progress", (value, label))))
            self.events.put(("success", result))
        except Exception as exc:
            self.events.put(("error", str(exc)))

    def poll_events(self) -> None:
        """Applica avanzamento ed esiti sul thread principale di Tk."""
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "progress":
                    value, label = payload
                    self.bar["value"] = value
                    self.status.set(label)
                else:
                    self.busy = False
                    for control in (self.entry, self.browse, self.create):
                        control.configure(state="normal")
                    if kind == "success":
                        self.status.set(f"Creato: {payload}")
                        messagebox.showinfo("Trasferimento completato", f"Archivio creato:\n{payload}\n\nSul nuovo PC estrarre tutto ed eseguire installa.bat.", parent=self)
                    else:
                        self.status.set("Creazione non completata.")
                        messagebox.showerror("Errore di trasferimento", str(payload), parent=self)
        except queue.Empty:
            pass
        self.after(100, self.poll_events)

    def close_window(self) -> None:
        """Evita di interrompere backup o pubblicazione mentre sono in corso."""
        if self.busy:
            messagebox.showinfo("Operazione in corso", "Attendere il completamento prima di chiudere.", parent=self)
        else:
            self.destroy()


def main() -> None:
    """Inizializza il terminale e avvia il generatore grafico."""
    init_terminal("TRASFERIMENTO STRUMENTI - LIS")
    TransferWindow().mainloop()


if __name__ == "__main__":
    main()
