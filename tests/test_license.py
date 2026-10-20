"""Contenuti legali coerenti e accessibili offline, prima e dopo il login."""

from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

from src import __author__
from src.gui.license_dialog import LicenseDialog, REPOSITORY_URL, read_legal_file
import trasfer

ROOT = Path(__file__).resolve().parents[1]
NOTICE = ("Il software costituisce uno strumento di supporto operativo. "
          "L'utilizzatore è tenuto a verificare autonomamente la correttezza, "
          "l'affidabilità e l'adeguatezza dei risultati ottenuti prima del loro "
          "impiego per finalità professionali, tecniche, scientifiche o decisionali.")


def test_legal_notice_and_attribution_match_readme():
    """Il testo visualizzato nell'app non deve divergere dal disclaimer richiesto."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    legal = (ROOT / "LEGAL.md").read_text(encoding="utf-8")
    heading = "## Esclusione di garanzia e limitazione di responsabilità"
    assert readme.split(heading, 1)[1].strip() == legal.split(heading, 1)[1].strip()
    for text in (readme, legal):
        assert NOTICE in text
        assert __author__ in text and REPOSITORY_URL in text
        assert "AGPL-3.0-or-later" in text
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert {"name": __author__} in metadata["project"]["authors"]
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in (ROOT / "LICENSE").read_text()
    assert "LEGAL.md" in trasfer.RUNTIME_FILES
    assert "src/gui/license_dialog.py" in trasfer.RUNTIME_FILES


def test_missing_legal_file_does_not_crash(tmp_path):
    """Un'installazione incompleta mostra il file da ripristinare."""
    assert "Impossibile caricare LICENSE" in read_legal_file(tmp_path, "LICENSE")


def test_license_dialog_contains_complete_read_only_text(ctk_root, monkeypatch):
    """La licenza integrale resta intatta e il link si apre solo su richiesta."""
    opened = []
    monkeypatch.setattr("src.gui.license_dialog.webbrowser.open", lambda url: opened.append(url))
    dialog = LicenseDialog(ctk_root)
    try:
        assert not opened
        assert NOTICE in dialog.disclaimer_text.get("1.0", "end")
        assert __author__ in dialog.disclaimer_text.get("1.0", "end")
        assert dialog.license_text.get("1.0", "end-1c") == (ROOT / "LICENSE").read_text(encoding="utf-8")
        assert dialog.disclaimer_text.cget("state") == "disabled"
        assert dialog.license_text.cget("state") == "disabled"
        dialog.repository_button.invoke()
        assert opened == [REPOSITORY_URL]
    finally:
        dialog.destroy()


def test_main_menu_available_before_login_and_for_both_roles(tmp_path):
    """Usa una vera root separata per evitare due interpreti Tk nella fixture."""
    code = """
import sys
from src.database import Database
from src.gui.app_window import AppWindow
db = Database(sys.argv[1])
app = AppWindow(db, check_updates=False)
try:
    assert app.main_menu.entrycget(0, 'label') == 'Licenza e responsabilità'
    app.main_menu.invoke(0)
    dialog = app._license_dialog
    assert dialog.winfo_exists()
    for role in ('OPERATORE', 'ADMIN'):
        user = db.get_user_by_username('admin')
        user.role = role
        app.show_dashboard(user)
        app.main_menu.invoke(0)
        assert app._license_dialog is dialog
    app.show_login()
    app.main_menu.invoke(0)
    assert app._license_dialog is dialog
    dialog.destroy()
    app.main_menu.invoke(0)
    assert app._license_dialog is not dialog
finally:
    app.destroy()
"""
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path / "menu.db")],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
