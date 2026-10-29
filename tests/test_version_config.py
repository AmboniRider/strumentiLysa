"""Test per la gestione, visualizzazione e configurazione della versione software.

La versione reale del programma non dipende da valori modificabili nel database.
"""

from pathlib import Path
import subprocess
import sys
import customtkinter as ctk
import pytest

from src import __version__
from src.auth import SessionManager
from src.config import DEFAULT_APP_VERSION, AppConfig
from src.database import Database
from src.gui.app_window import AppWindow
from src.gui.master_detail import MasterDetailView
from src.gui.settings_dialog import SettingsDialog
from src.models import UserRecord
from src.gui.update_dialog import UpdateController, UpdateDialog


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    """Fixture per istanziare un database di test isolato."""
    db_file = tmp_path / "version_test.db"
    return Database(db_file)


@pytest.fixture
def admin_user() -> UserRecord:
    """Fixture per utente admin fittizio."""
    return UserRecord(
        id=1,
        username="admin",
        password_hash="hash",
        salt="salt",
        role="ADMIN",
    )


def test_default_app_version_in_config_and_db(test_db: Database):
    """Verifica l'allineamento della versione iniziale con il programma installato."""
    # 1. Config iniziale
    config = test_db.get_config()
    assert config.app_version == DEFAULT_APP_VERSION
    assert config.app_version == __version__

    # 2. Controllo valore memorizzato nella tabella configurations
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM configurations WHERE key = 'app_version'")
        row = cursor.fetchone()
        assert row is not None
        assert row["value"] == __version__


def test_update_app_version_persistence(test_db: Database):
    """Un vecchio valore configurabile non sostituisce la versione del codice."""
    test_db.save_config_value("app_version", "1.5.0")
    config = test_db.get_config()
    assert config.app_version == __version__

    # Salva tutte le configurazioni preservando la versione
    test_db.save_all_configs(config)
    config_reloaded = test_db.get_config()
    assert config_reloaded.app_version == __version__


def test_app_window_title_with_version(test_db: Database):
    """Una finestra principale vive in un interprete separato da quello fixture Tk."""
    code = """
import sys
from src import __version__
from src.database import Database
from src.gui.app_window import AppWindow
app = AppWindow(Database(sys.argv[1]), check_updates=False)
try:
    assert app.title().endswith('Versione ' + __version__)
    view = app.current_view
    app.db.save_config_value('app_version', '99.0')
    app.update_app_title()
    assert app.title().endswith('Versione ' + __version__)
    assert app.current_view is view
finally:
    app.destroy()
"""
    result = subprocess.run([sys.executable, "-c", code, str(test_db.db_path)],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr


def test_master_detail_brand_label_with_version(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk):
    """Verifica che la testata interna mostri '🔬 STRUMENTI ➔ LIS v{version}' e si aggiorni."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        view = MasterDetailView(
            master=ctk_root,
            db=test_db,
            current_user=admin_user,
            on_logout=lambda: None
        )

        assert hasattr(view, "lbl_brand")
        assert f"v{__version__}" in view.lbl_brand.cget("text")

        # Simula cambio versione e aggiornamento vista
        test_db.save_config_value("app_version", "1.2")
        view.update_version_display()
        assert f"v{__version__}" in view.lbl_brand.cget("text")

        view.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()


def test_settings_version_is_read_only(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk):
    """La versione installata non può essere riscritta dalle impostazioni."""
    SessionManager.set_user(admin_user)
    dialog = SettingsDialog(ctk_root, test_db)
    try:
        assert dialog.version_label.cget("text") == __version__
        assert not hasattr(dialog, "entry_version")
        assert not hasattr(dialog, "_save_version")
    finally:
        dialog.destroy()
        SessionManager.logout()


def test_update_panel_admin_controls(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk):
    """Il pannello reale espone backup/verifica e disabilita installazioni inesistenti."""
    SessionManager.set_user(admin_user)
    controller = UpdateController(ctk_root)
    dialog = UpdateDialog(ctk_root, test_db, controller)
    try:
        ctk_root.update_idletasks()
        assert dialog.backup_button.cget("text") == "Crea copia database"
        assert dialog.install_button.cget("state") == "disabled"
        assert dialog.check_button.cget("state") == "normal"
        assert dialog.intranet_button.cget("text") == "Aggiorna tramite intranet"
        assert dialog.intranet_button.cget("state") == "normal"
        SessionManager.logout()
        with pytest.raises(PermissionError):
            dialog._backup()
        with pytest.raises(PermissionError):
            dialog._check_intranet()
    finally:
        dialog._close()
        controller.close()
        SessionManager.logout()
