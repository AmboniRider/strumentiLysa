"""Regressioni per eliminazione utenti, conservazione audit e messaggi GUI."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import Mock

import pytest

from src.auth import SessionManager
from src.database import Database
from src.gui.settings_dialog import SettingsDialog, messagebox


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Prepara account ed eventi sintetici senza accedere ai dati operativi."""
    database = Database(tmp_path / "users.db")
    assert database.add_user("operatore", "test-only", "OPERATORE")[0]
    user = database.get_user_by_username("operatore")
    admin = database.get_user_by_username("admin")
    database.log_action(user.id, user.username, "USER_LOGIN", "Accesso di prova")
    database.log_action(user.id, user.username, "IMPORT", "Importazione di prova")
    database.log_action(admin.id, admin.username, "USER_LOGIN", "Accesso admin")
    return database


def audit_rows(db: Database) -> list[tuple]:
    """Legge tutti i campi per rilevare perdite o alterazioni dello storico."""
    with db.get_connection() as conn:
        return [tuple(row) for row in conn.execute("SELECT * FROM audit_logs ORDER BY id")]


def add_blocking_reference(db: Database, user_id: int) -> None:
    """Simula un ulteriore vincolo per verificare il rollback delle due scritture."""
    with db.get_connection() as conn:
        conn.execute("CREATE TABLE retained_references (user_id INTEGER REFERENCES users(id))")
        conn.execute("INSERT INTO retained_references VALUES (?)", (user_id,))


def test_delete_user_preserves_audit_and_foreign_keys(db: Database) -> None:
    """Un account con eventi si elimina mantenendo nomi, dettagli e timestamp."""
    user = db.get_user_by_username("operatore")
    admin = db.get_user_by_username("admin")
    before = audit_rows(db)

    ok, message = db.delete_user(user.id, admin.id)

    assert ok, message
    assert db.get_user_by_username("operatore") is None
    # L'unica variazione consentita è user_id negli eventi dell'account eliminato.
    expected = [(row[0], None, *row[2:]) if row[1] == user.id else row for row in before]
    assert audit_rows(db) == expected
    with db.get_connection() as conn:
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_delete_user_without_audit(db: Database) -> None:
    """La cancellazione rimane valida anche senza riferimenti allo storico."""
    assert db.add_user("senza_eventi", "test-only", "OPERATORE")[0]
    user = db.get_user_by_username("senza_eventi")
    admin = db.get_user_by_username("admin")
    before = audit_rows(db)
    assert db.delete_user(user.id, admin.id)[0]
    assert db.get_user_by_username(user.username) is None
    assert audit_rows(db) == before


@pytest.mark.parametrize("case", ["self", "last_admin", "missing"])
def test_delete_user_protections_preserve_audit(db: Database, case: str) -> None:
    """I rifiuti precedenti all'eliminazione lasciano intatti account e riferimenti."""
    admin = db.get_user_by_username("admin")
    user = db.get_user_by_username("operatore")
    ids_and_messages = {
        "self": (user.id, user.id, "stesso account"),
        "last_admin": (admin.id, user.id, "unico utente Amministratore"),
        "missing": (999999, admin.id, "non trovato"),
    }
    target, actor, expected = ids_and_messages[case]
    before = audit_rows(db)
    ok, message = db.delete_user(target, actor)
    assert not ok and expected in message
    assert audit_rows(db) == before
    assert db.get_user_by_username("admin") is not None
    assert db.get_user_by_username("operatore") is not None


def test_delete_one_of_two_admins(db: Database) -> None:
    """Un secondo amministratore può essere eliminato senza perdere il suo audit."""
    assert db.add_user("altro_admin", "test-only", "ADMIN")[0]
    target = db.get_user_by_username("altro_admin")
    actor = db.get_user_by_username("admin")
    db.log_action(target.id, target.username, "USER_LOGIN")
    assert db.delete_user(target.id, actor.id)[0]
    assert db.get_user_by_username(target.username) is None
    assert audit_rows(db)[-1][1:3] == (None, target.username)


def test_delete_user_rolls_back_audit_on_other_constraint(db: Database) -> None:
    """Un ulteriore vincolo produce un messaggio e ripristina gli ID dell'audit."""
    user = db.get_user_by_username("operatore")
    admin = db.get_user_by_username("admin")
    add_blocking_reference(db, user.id)
    before = audit_rows(db)

    ok, message = db.delete_user(user.id, admin.id)

    assert not ok and "riferimento" in message
    assert db.get_user_by_username("operatore") is not None
    assert audit_rows(db) == before
    with db.get_connection() as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_delete_user_handles_database_unavailable(db: Database, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un errore di apertura connessione non deve sfuggire al callback Tk."""
    @contextmanager
    def unavailable() -> Iterator[sqlite3.Connection]:
        raise sqlite3.OperationalError("database is locked")
        yield  # Mantiene il contratto di context manager della connessione.

    monkeypatch.setattr(db, "get_connection", unavailable)
    ok, message = db.delete_user(2, 1)
    assert not ok and "errore del database" in message


@pytest.mark.parametrize("blocked", [False, True])
def test_delete_user_gui_callback(db: Database, monkeypatch: pytest.MonkeyPatch, blocked: bool) -> None:
    """Il callback reale aggiorna l'elenco o mostra l'errore, senza finestre modali."""
    user = db.get_user_by_username("operatore")
    admin = db.get_user_by_username("admin")
    if blocked:
        add_blocking_reference(db, user.id)
    tree = Mock()
    tree.selection.return_value = ("selected",)
    tree.item.return_value = {"values": [user.id, user.username]}
    dialog = SimpleNamespace(db=db, tree_users=tree, _refresh_users_list=Mock())
    showerror = Mock()
    monkeypatch.setattr(SessionManager, "get_user", staticmethod(lambda: admin))
    monkeypatch.setattr(messagebox, "askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(messagebox, "showerror", showerror)

    SettingsDialog._delete_user(dialog)

    assert showerror.call_count == int(blocked)
    assert dialog._refresh_users_list.call_count == int(not blocked)
    assert (db.get_user_by_username(user.username) is not None) == blocked
