# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
# Copyright (C) 2026 Strumenti-LIS Contributors
# Distributed under the terms of the GNU Affero General Public License v3 or later.

"""Entry point principale per l'applicazione Strumenti - LIS.

Questo script inizializza il terminale con il banner ANSI e il titolo della console
(secondo le regole definite in AGENTS.md), avvia la connessione al database SQLite
e lancia l'interfaccia grafica CustomTkinter.
"""

from __future__ import annotations

import os
import sys

# Il bootstrap usa solo la libreria standard: recupera il runtime prima che
# import di terze parti o migrazioni possano aprire un'installazione incompleta.
if __name__ == "__main__":
    from pathlib import Path
    from update_runner import bootstrap
    try:
        bootstrap(Path(__file__).resolve().parent)
    except Exception as exc:
        import tkinter.messagebox
        tkinter.messagebox.showerror("Avvio non disponibile", str(exc))
        raise SystemExit(1)

# Forza l'output UTF-8 per supportare i caratteri grafici ANSI e Unicode su console Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.database import Database
from src.gui import AppWindow


def init_terminal(title: str) -> None:
    """Imposta il titolo della finestra console e stampa il banner grafico ANSI all'avvio."""
    # Imposta titolo console (Windows API e sequenza ANSI standard)
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass

    try:
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()
    except Exception:
        pass

    # Colori ANSI brillanti
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

    box = "═" * (len(title) + 8)
    try:
        print(f"\n{YELLOW}╔{box}╗{RESET}")
        print(f"{YELLOW}║    {CYAN}{title}{YELLOW}    ║{RESET}")
        print(f"{YELLOW}╚{box}╝{RESET}")
        print(f"{GREEN}▶ Interfaccia Strumenti di Laboratorio -> LIS{RESET}")
        print(f"{GREEN}▶ Database SQLite e Ambiente inizializzati con successo.{RESET}\n")
    except UnicodeEncodeError:
        # Fallback ASCII per console con codifica legacy
        ascii_box = "=" * (len(title) + 8)
        print(f"\n+{ascii_box}+")
        print(f"|    {title}    |")
        print(f"+{ascii_box}+\n")


def main() -> None:
    """Funzione principale di avvio dell'applicazione."""
    app_title = "STRUMENTI DI LABORATORIO -> LIS"
    init_terminal(app_title)

    # Inizializza o apre il database SQLite locale
    db = Database()

    # Avvia l'interfaccia grafica CustomTkinter
    app = AppWindow(db)
    app.mainloop()


if __name__ == "__main__":
    main()
