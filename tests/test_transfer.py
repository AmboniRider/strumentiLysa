"""Verifica trasferimento, isolamento dei dati e primo avvio in una nuova cartella."""

from datetime import datetime
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
from zipfile import ZipFile

import pytest

import trasfer
from src.database import Database


@pytest.fixture
def transfer_source(tmp_path: Path) -> Path:
    """Copia il runtime reale e crea dati sintetici senza leggere il DB operativo."""
    root = tmp_path / "sorgente con spazi è"
    root.mkdir()
    for relative in trasfer.RUNTIME_FILES:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(trasfer.PROJECT_ROOT / relative, target)
    db = Database(root / "data/strumenti.db")
    with db.get_connection() as conn:
        conn.execute("UPDATE configurations SET value='7.4' WHERE key='app_version'")
        conn.execute("UPDATE configurations SET value='Z:/vecchio_pc/sequenze' WHERE key='path_input'")
        conn.execute("UPDATE transcodings SET lis_exam_code='PERSONALIZZATO', lis_substance_code='00500' WHERE id=1")
        # Stringhe lunghe verificano che anche pagine overflow/libere vengano ripulite.
        marker = "CAMPIONE_DA_NON_TRASFERIRE_" * 2000
        conn.execute("""INSERT INTO samples (sample_code, lab_code, year, acceptance,
            conferment, sample_number, source_filename) VALUES
            ('BG2600104430010001', 'BG', 26, '10443', 1, 1, ?)""", (marker,))
        conn.execute("""INSERT INTO sample_results
            (sample_id, param_name, raw_value, formatted_value)
            VALUES (1, 'Parametro', ?, '1,0')""", (marker,))
        conn.execute("INSERT INTO audit_logs (username, action, details) VALUES ('admin', 'IMPORT_FILES', ?)", (marker,))
    # File estranei anche sotto directory incluse: nessuno va nello ZIP.
    for relative in ("sync.bat", ".env", "tests/test_private.py", "src/.env",
                     "src/__pycache__/config.pyc", "export/vecchio.csv", "sequenze/dato.txt"):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("NON_INCLUDERE", encoding="utf-8")
    return root


def snapshot(database: Path) -> str:
    """Restituisce lo stato logico per rilevare qualunque modifica al sorgente."""
    conn = sqlite3.connect(database)
    try:
        return "\n".join(conn.iterdump())
    finally:
        conn.close()


def test_zip_contents_and_sanitized_database(transfer_source: Path, tmp_path: Path):
    """Controlla whitelist, conservazione account/config e rimozione fisica dei dati."""
    before = snapshot(transfer_source / "data/strumenti.db")
    output = tmp_path / "destinazione è"
    output.mkdir()
    updates = []
    result = trasfer.create_transfer(output, transfer_source, lambda n, text: updates.append(n))
    with ZipFile(result) as archive:
        assert archive.testzip() is None
        assert b"Agilent 5977C" in archive.read("strumenti/driver_implementati/agilent_5977c.md")
        assert set(archive.namelist()) == {"strumenti/" + p for p in trasfer.RUNTIME_FILES} | {
            "strumenti/data/strumenti.db", "strumenti/installa.bat", "strumenti/strumenti.bat"}
        db_bytes = archive.read("strumenti/data/strumenti.db")
        assert b"CAMPIONE_DA_NON_TRASFERIRE" not in db_bytes
        assert b"BG2600104430010001" not in db_bytes
        assert b"Z:/vecchio_pc/sequenze" not in db_bytes
        archive.extractall(output)
        for bat in ("installa.bat", "strumenti.bat"):
            content = archive.read("strumenti/" + bat)
            assert b"\r\n" in content and b"\n" not in content.replace(b"\r\n", b"")
    conn = sqlite3.connect(output / "strumenti/data/strumenti.db")
    try:
        for table in ("samples", "sample_results", "audit_logs"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        assert conn.execute("SELECT name FROM sqlite_sequence WHERE name IN ('samples', 'sample_results', 'audit_logs')").fetchall() == []
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
        assert conn.execute("SELECT value FROM configurations WHERE key='app_version'").fetchone()[0] == "7.4"
        assert conn.execute("SELECT lis_exam_code FROM transcodings WHERE id=1").fetchone()[0] == "PERSONALIZZATO"
        assert conn.execute("SELECT lis_substance_code FROM transcodings WHERE id=1").fetchone()[0] == "00500"
        assert conn.execute("SELECT key FROM configurations WHERE key LIKE 'path_%'").fetchall() == []
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()
    assert snapshot(transfer_source / "data/strumenti.db") == before
    assert updates[0] == 0 and updates[-1] == 100 and updates == sorted(updates)
    assert not list(output.glob(".transfer-*"))


def test_backup_includes_committed_wal(transfer_source: Path, tmp_path: Path):
    """Mantiene il WAL aperto: la configurazione più recente deve essere trasferita."""
    original = sqlite3.connect(transfer_source / "data/strumenti.db")
    try:
        original.execute("PRAGMA journal_mode=WAL")
        original.execute("PRAGMA wal_autocheckpoint=0")
        original.execute("UPDATE configurations SET value='WAL-RECENTE' WHERE key='app_version'")
        original.commit()
        assert (transfer_source / "data/strumenti.db-wal").stat().st_size > 0
        clean = tmp_path / "clean.db"
        trasfer.sanitized_database(transfer_source / "data/strumenti.db", clean)
        with sqlite3.connect(clean) as conn:
            assert conn.execute("SELECT value FROM configurations WHERE key='app_version'").fetchone()[0] == "WAL-RECENTE"
        assert original.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 1
    finally:
        original.close()


@pytest.mark.parametrize("missing", ["manuale.md", "src/gui/help_dialog.py", "data/strumenti.db"])
def test_missing_required_file(transfer_source: Path, tmp_path: Path, missing: str):
    """File assenti interrompono l'operazione prima della creazione di temporanei."""
    (transfer_source / missing).rename(transfer_source / "temporaneamente_assente")
    with pytest.raises(trasfer.TransferError, match="obbligatorio"):
        trasfer.create_transfer(tmp_path, transfer_source)
    assert not list(tmp_path.glob("*.zip"))


@pytest.mark.parametrize("unknown_schema", [False, True])
def test_invalid_database(transfer_source: Path, tmp_path: Path, unknown_schema: bool):
    """Corruzione e nuove tabelle non devono finire in uno ZIP distribuito."""
    db = transfer_source / "data/strumenti.db"
    if unknown_schema:
        with sqlite3.connect(db) as conn:
            conn.execute("CREATE TABLE future_samples (secret TEXT)")
    else:
        db.write_bytes(b"not a sqlite database")
    with pytest.raises(trasfer.TransferError):
        trasfer.create_transfer(tmp_path, transfer_source)
    assert not list(tmp_path.glob("*.zip"))
    assert not list(tmp_path.glob(".transfer-*"))


def test_collision_preserves_existing_zip(transfer_source: Path, tmp_path: Path, monkeypatch):
    """Due richieste con stesso timestamp non possono sovrascrivere il primo ZIP."""
    class FrozenDate:
        @staticmethod
        def now():
            return datetime(2026, 10, 6, 12, 0, 0)
    monkeypatch.setattr(trasfer, "datetime", FrozenDate)
    existing = trasfer.create_transfer(tmp_path, transfer_source)
    before = existing.read_bytes()
    with pytest.raises(trasfer.TransferError, match="già esistente"):
        trasfer.create_transfer(tmp_path, transfer_source)
    assert existing.read_bytes() == before
    assert not list(tmp_path.glob(".transfer-*"))


def test_write_failure_leaves_no_zip(transfer_source: Path, tmp_path: Path, monkeypatch):
    """Simula disco pieno durante la compressione verificando la pulizia dello staging."""
    def fail_write(*args, **kwargs):
        raise OSError("Spazio insufficiente")
    monkeypatch.setattr(trasfer.ZipFile, "write", fail_write)
    with pytest.raises(OSError, match="Spazio"):
        trasfer.create_transfer(tmp_path, transfer_source)
    assert not list(tmp_path.glob("*.zip"))
    assert not list(tmp_path.glob(".transfer-*"))


def test_no_destination_write_permission(transfer_source: Path, tmp_path: Path, monkeypatch):
    """Simula permessi mancanti senza dipendere dai privilegi dell'utente dei test."""
    def denied(*args, **kwargs):
        raise PermissionError("Accesso negato")
    monkeypatch.setattr(trasfer.tempfile, "TemporaryDirectory", denied)
    with pytest.raises(PermissionError):
        trasfer.create_transfer(tmp_path, transfer_source)
    assert not list(tmp_path.glob("*.zip"))


def test_extracted_first_start_and_help(transfer_source: Path, tmp_path: Path):
    """Un processo nuovo importa i moduli estratti, verifica account, percorsi e help."""
    result = trasfer.create_transfer(tmp_path, transfer_source)
    with ZipFile(result) as archive:
        archive.extractall(tmp_path / "nuovo pc è")
    root = tmp_path / "nuovo pc è/strumenti"
    code = '''
from pathlib import Path
import src
from src.auth import verify_password
from src.config import BASE_DIR
from src.database import Database
from src.gui.app_window import AppWindow
from src.gui.help_dialog import HelpDialog
assert BASE_DIR == Path.cwd()
assert Path(src.__file__).is_relative_to(Path.cwd())
db = Database()
user = db.get_user_by_username('admin')
assert verify_password('admin', user.password_hash, user.salt)
config = db.get_config()
assert config.input_dir == BASE_DIR / 'sequenze'
assert config.archive_dir == BASE_DIR / 'archiviati'
assert config.error_dir == BASE_DIR / 'errori'
assert config.export_dir == BASE_DIR / 'export'
assert db.get_samples() == []
app = AppWindow(db)
app.withdraw()
app.show_dashboard(user)
help_window = HelpDialog(app)
assert help_window.manual_path == BASE_DIR / 'manuale.md'
assert 'Strumenti' in help_window.txt_content.get('1.0', 'end')
help_window.destroy()
app.destroy()
custom = str(BASE_DIR / 'personalizzata')
db.save_config_value('path_input', custom)
assert Database().get_config().input_dir == Path(custom)
print('Primo avvio, account, cartelle e help verificati')
'''
    process = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, timeout=45)
    assert process.returncode == 0, process.stderr


def test_ttk_worker_reports_success(transfer_source: Path, tmp_path: Path):
    """Verifica GUI/worker reali in un processo Tk isolato dalla suite CTk.

    Gli interpreti Tk e i cicli dei widget di altri test non devono convivere
    con il thread di trasferimento: su Windows possono causare arresti nativi.
    Le verifiche restano identiche e ogni errore del processo fa fallire il test.
    """
    code = r'''
import sys
import time
from pathlib import Path
import trasfer

original = trasfer.create_transfer
source = Path(sys.argv[1])
trasfer.create_transfer = lambda destination, progress: original(destination, source, progress)
messages, errors = [], []
trasfer.messagebox.showinfo = lambda *a, **k: messages.append(a)
trasfer.messagebox.showerror = lambda *a, **k: errors.append(a)
window = trasfer.TransferWindow()
window.withdraw()
try:
    window.destination.set(sys.argv[2])
    window.start_transfer()
    assert window.busy
    assert str(window.create['state']) == 'disabled'
    deadline = time.monotonic() + 15
    while window.busy and time.monotonic() < deadline:
        window.update()
        time.sleep(0.01)
    assert not window.busy
    assert not errors, errors
    assert messages and window.bar['value'] == 100
    assert str(window.create['state']) == 'normal'
finally:
    window.destroy()
'''
    process = subprocess.run([sys.executable, "-c", code, str(transfer_source), str(tmp_path)],
                             cwd=trasfer.PROJECT_ROOT, capture_output=True, text=True, timeout=45)
    assert process.returncode == 0, process.stdout + process.stderr
