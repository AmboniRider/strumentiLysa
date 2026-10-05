"""Test per la gestione, visualizzazione e configurazione della versione software.

Verifica che la versione predefinita sia '1.0', che venga visualizzata correttamente
nel titolo della finestra principale e nella testata interna, e che l'Amministratore
possa aggiornarla dinamicamente dal pannello Impostazioni.
"""

from pathlib import Path
import customtkinter as ctk
import pytest

from src.auth import SessionManager
from src.config import DEFAULT_APP_VERSION, AppConfig
from src.database import Database
from src.gui.app_window import AppWindow
from src.gui.master_detail import MasterDetailView
from src.gui.settings_dialog import SettingsDialog
from src.models import UserRecord


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
    """Verifica che la versione di default sia '1.0' sia in AppConfig che nel database SQLite."""
    # 1. Config iniziale
    config = test_db.get_config()
    assert config.app_version == DEFAULT_APP_VERSION
    assert config.app_version == "1.0"

    # 2. Controllo valore memorizzato nella tabella configurations
    with test_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM configurations WHERE key = 'app_version'")
        row = cursor.fetchone()
        assert row is not None
        assert row["value"] == "1.0"


def test_update_app_version_persistence(test_db: Database):
    """Verifica che la modifica della versione nel database venga persistita correttamente."""
    test_db.save_config_value("app_version", "1.5.0")
    config = test_db.get_config()
    assert config.app_version == "1.5.0"

    # Salva tutte le configurazioni preservando la versione
    test_db.save_all_configs(config)
    config_reloaded = test_db.get_config()
    assert config_reloaded.app_version == "1.5.0"


def test_app_window_title_with_version(test_db: Database, ctk_root: ctk.CTk):
    """Verifica che il titolo della finestra principale includa la versione corrente."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        app = AppWindow(test_db)
        title = app.title()
        assert "Versione 1.0" in title
        assert "Interfaccia Strumenti di Laboratorio - LIS - Versione 1.0" == title

        # Modifica versione nel database e chiama update_app_title
        test_db.save_config_value("app_version", "2.1")
        app.update_app_title()
        assert "Versione 2.1" in app.title()

        app.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()


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
        assert "v1.0" in view.lbl_brand.cget("text")

        # Simula cambio versione e aggiornamento vista
        test_db.save_config_value("app_version", "1.2")
        view.update_version_display()
        assert "v1.2" in view.lbl_brand.cget("text")

        view.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()


def test_settings_dialog_version_save_and_propagation(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk, monkeypatch: pytest.MonkeyPatch):
    """Verifica che l'amministratore possa modificare la versione in SettingsDialog e che i titoli si aggiornino."""
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *args, **kwargs: None)
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        SessionManager.set_user(admin_user)
        callback_called = False

        def on_change():
            nonlocal callback_called
            callback_called = True

        dlg = SettingsDialog(ctk_root, test_db, on_config_changed=on_change)

        # Verifica presenza del campo versione precompilato con '1.0'
        assert hasattr(dlg, "entry_version")
        assert dlg.entry_version.get() == "1.0"

        # Modifica la versione a '3.0.0-PROD'
        dlg.entry_version.delete(0, "end")
        dlg.entry_version.insert(0, "3.0.0-PROD")
        dlg._save_version()

        # Verifica persistenza nel database
        assert test_db.get_config().app_version == "3.0.0-PROD"
        # Verifica invocazione callback di notifica
        assert callback_called is True

        # Verifica log di audit
        with test_db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs WHERE action = 'CONFIG_VERSION_UPDATE'")
            log_row = cursor.fetchone()
            assert log_row is not None
            assert "3.0.0-PROD" in log_row["details"]

        dlg.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()
        SessionManager.logout()


def test_settings_dialog_rejects_empty_version(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk, monkeypatch: pytest.MonkeyPatch):
    """Verifica che una versione vuota o composta solo da spazi venga rifiutata."""
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *args, **kwargs: None)
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        SessionManager.set_user(admin_user)
        dlg = SettingsDialog(ctk_root, test_db)

        dlg.entry_version.delete(0, "end")
        dlg.entry_version.insert(0, "   ")
        dlg._save_version()

        # Il valore nel DB deve rimanere invariato ('1.0')
        assert test_db.get_config().app_version == "1.0"

        dlg.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()
        SessionManager.logout()
