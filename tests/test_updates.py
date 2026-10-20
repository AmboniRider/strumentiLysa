"""Regressioni del protocollo Release, database, backup e rollback su copie."""

from contextlib import closing
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sqlite3
from types import SimpleNamespace
from unittest.mock import Mock
from zipfile import ZipFile

import pytest

import build_release
import maintenance
import trasfer
import update_runner
from src import __version__
from src.auth import SessionManager, verify_password
from src.backup import copy_database, dated_backup
from src.database import Database
from src.gui.update_dialog import UpdateController, UpdateDialog, require_admin
from src.update_service import (Release, UpdateError, check_release, safe_runtime_path,
                                stage_release, validate_manifest, version_tuple)
import src.update_service as service


@pytest.fixture
def package(tmp_path: Path) -> tuple[dict, bytes]:
    """Produce il vero pacchetto e non include alcun database di laboratorio."""
    manifest_path = build_release.build_release(trasfer.PROJECT_ROOT, tmp_path / "release")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    archive = next(manifest_path.parent.glob("*.zip"))
    return manifest, archive.read_bytes()


@pytest.fixture
def installation(tmp_path: Path) -> Path:
    """Postazione sintetica senza .git e con ambiente fittizio per i test di guasto."""
    root = tmp_path / "installazione con spazi è"
    root.mkdir()
    for name in trasfer.RUNTIME_FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(trasfer.PROJECT_ROOT / name, target)
    (root / ".venv/Scripts").mkdir(parents=True)
    (root / ".venv/Scripts/python.exe").write_text("vecchio ambiente")
    (root / ".tools").mkdir()
    (root / ".tools/uv.exe").write_text("fake")
    db = Database(root / "data/strumenti.db")
    db.save_config_value("allowed_labs", "BG,MI")
    return root


def release_for(manifest: dict) -> Release:
    """Incapsula un manifest di test senza consultare GitHub."""
    return Release(manifest["version"], "Novità di prova", "https://github.com/AmboniRider/strumentiLysa/releases", manifest)


def stage(monkeypatch, installation: Path, package: tuple[dict, bytes]) -> Path:
    """Scarica bytes controllati lasciando reali checksum ed estrazione."""
    manifest, payload = package
    monkeypatch.setattr(service, "download", lambda *args: payload)
    monkeypatch.setattr(service.shutil, "disk_usage", lambda root: SimpleNamespace(free=10**12))
    return stage_release(release_for(manifest), installation, 1)


def logical(path: Path) -> str:
    """Confronto logico indipendente da checkpoint e paginazione SQLite."""
    with closing(sqlite3.connect(path)) as conn:
        return "\n".join(conn.iterdump())


def test_version_ordering():
    assert version_tuple("1.10") > version_tuple("v1.9.99")
    assert version_tuple("v1.2.0") == version_tuple("1.2")
    with pytest.raises(UpdateError):
        version_tuple("1.2.0rc1")


@pytest.mark.parametrize("name", ["../data/strumenti.db", "src/../../app.py", "/app.py", "src\\auth.py", ".git/config", "data/strumenti.db", "src/.env", "src/__pycache__/x.py", "C:/app.py"])
def test_archive_paths_rejected(name):
    assert not safe_runtime_path(name)


def test_build_contains_only_runtime(package):
    manifest, payload = package
    with ZipFile(io.BytesIO(payload)) as archive:
        assert set(archive.namelist()) == set(trasfer.RUNTIME_FILES) | {"strumenti.bat"}
        assert all(safe_runtime_path(name) for name in archive.namelist())
        assert hashlib.sha256(payload).hexdigest() == manifest["package"]["sha256"]


@pytest.mark.parametrize("broken", ["hash", "url", "policy", "files", "python", "version", "losses"])
def test_invalid_manifest_is_blocked(package, broken):
    manifest = deepcopy(package[0])
    if broken == "hash":
        manifest["package"]["sha256"] = "invalid"
    elif broken == "url":
        manifest["package"]["url"] = "http://evil.example/update.zip"
    elif broken == "policy":
        manifest["database"]["mode"] = "unknown"
    elif broken == "files":
        manifest["files"]["data/strumenti.db"] = "0" * 64
    elif broken == "python":
        manifest["python"]["min"] = [99, 0]
    elif broken == "version":
        manifest["version"] = "1.1.0"
    else:
        manifest["database"]["mode"] = "reset"
    with pytest.raises(UpdateError):
        validate_manifest(manifest, __version__)


def test_release_selects_stable_and_ignores_drafts(monkeypatch, package):
    manifest, _ = package
    entry = {"tag_name": "v" + __version__, "body": "Novità", "html_url": "https://github.com/release",
             "assets": [{"name": "update-manifest.json", "browser_download_url": manifest["package"]["url"] + ".json"}]}
    entries = [{**entry, "tag_name": "v99.0.0", "draft": True},
               {**entry, "tag_name": "v98.0.0", "prerelease": True}, entry]
    monkeypatch.setattr(service, "download", lambda url, limit: json.dumps(entries if url == service.API else manifest).encode())
    assert check_release("1.1.0").version == __version__
    assert check_release(__version__) is None


def test_empty_release_list_and_network_failure(monkeypatch):
    monkeypatch.setattr(service, "download", lambda *args: b"[]")
    assert check_release() is None
    monkeypatch.setattr(service, "download", Mock(side_effect=TimeoutError))
    with pytest.raises(UpdateError, match="connessione"):
        check_release()


def test_missing_manifest_blocks_update(monkeypatch):
    monkeypatch.setattr(service, "download", lambda *args: b'[{"tag_name":"v99.0.0","assets":[]}]')
    with pytest.raises(UpdateError, match="manifest"):
        check_release()


def test_stage_checks_archive_digest(monkeypatch, installation, package):
    monkeypatch.setattr(service, "download", lambda *args: b"altered")
    with pytest.raises(UpdateError, match="Checksum"):
        stage_release(release_for(package[0]), installation, 1)
    assert not list((installation / ".updates").iterdir())


def test_archive_extra_file_blocked(monkeypatch, installation, package):
    manifest, payload = deepcopy(package[0]), package[1]
    stream = io.BytesIO(payload)
    with ZipFile(stream, "a") as archive:
        archive.writestr("../danger.py", b"danger")
    payload = stream.getvalue()
    manifest["package"]["sha256"] = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(service, "download", lambda *args: payload)
    with pytest.raises(UpdateError, match="inattesi"):
        stage_release(release_for(manifest), installation, 1)


def test_dev_copy_reset_and_schema_guards(installation, package):
    release = release_for(deepcopy(package[0]))
    (installation / ".git").mkdir()
    with pytest.raises(UpdateError, match="sviluppo"):
        stage_release(release, installation, 1)
    (installation / ".git").rmdir()
    with pytest.raises(UpdateError, match="Schema"):
        stage_release(release, installation, 99)
    release.manifest["database"]["mode"] = "reset"
    with pytest.raises(UpdateError, match="confermata"):
        stage_release(release, installation, 1)


def test_backup_includes_wal_and_never_overwrites(tmp_path):
    db = Database(tmp_path / "source.db")
    with closing(sqlite3.connect(db.db_path)) as original:
        original.execute("PRAGMA wal_autocheckpoint=0")
        original.execute("UPDATE configurations SET value='DAL_WAL' WHERE key='allowed_labs'")
        original.commit()
        target = dated_backup(db.db_path, tmp_path)
        with closing(sqlite3.connect(target)) as copied:
            assert copied.execute("SELECT value FROM configurations WHERE key='allowed_labs'").fetchone()[0] == "DAL_WAL"
        content = target.read_bytes()
        with pytest.raises(FileExistsError):
            copy_database(db.db_path, target)
        assert target.read_bytes() == content


def test_backup_invalid_source_cleanup(tmp_path):
    source = tmp_path / "invalid.db"
    source.write_bytes(b"not a database")
    target = tmp_path / "backup.db"
    with pytest.raises(sqlite3.DatabaseError):
        copy_database(source, target)
    assert not target.exists()


def test_migration_failure_rolls_back_schema(tmp_path, monkeypatch):
    """DDL e numero di versione devono essere confermati nella stessa transazione."""
    path = tmp_path / "legacy.db"
    Database(path)
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("PRAGMA user_version=0")
    def broken(self, conn):
        conn.execute("CREATE TABLE migration_incomplete (id INTEGER)")
        raise ValueError("migrazione fallita")
    monkeypatch.setattr(Database, "_migrate_0_to_1", broken)
    with pytest.raises(ValueError, match="migrazione fallita"):
        Database(path)
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='migration_incomplete'").fetchone() is None


def test_schema_migration_and_future_refusal(tmp_path):
    path = tmp_path / "legacy.db"
    db = Database(path)
    with db.get_connection() as conn:
        conn.execute("PRAGMA user_version=0")
    before = logical(path)
    Database(path)
    assert logical(path) == before
    with db.get_connection() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        conn.execute("PRAGMA user_version=99")
    content = path.read_bytes()
    with pytest.raises(ValueError, match="più recente"):
        Database(path)
    assert path.read_bytes() == content


def test_reset_recovers_configuration_not_samples(installation, package, tmp_path):
    db = Database(installation / "data/strumenti.db")
    assert db.update_user_password(1, "modificata")[0]
    with db.get_connection() as conn:
        conn.execute("UPDATE transcodings SET description='personalizzata', is_active=0 WHERE id=1")
        conn.execute("INSERT INTO audit_logs (username, action) VALUES ('admin', 'TEST')")
        conn.execute("INSERT INTO samples (sample_code,lab_code,year,acceptance,conferment,sample_number,source_filename) VALUES ('BG2600104430010001','BG',26,'10443',1,1,'x.txt')")
    before = logical(db.db_path)
    manifest = deepcopy(package[0])
    manifest["database"].update(mode="reset", losses="Campioni, risultati e audit")
    target = tmp_path / "new.db"
    maintenance.prepare_database(db.db_path, target, manifest)
    assert logical(db.db_path) == before
    new = Database(target)
    admin = new.get_user_by_username("admin")
    assert verify_password("modificata", admin.password_hash, admin.salt)
    with db.get_connection() as old, new.get_connection() as copied:
        for table in ("users", "configurations", "transcodings"):
            assert list(map(tuple, old.execute(f"SELECT * FROM {table} ORDER BY 1"))) == list(map(tuple, copied.execute(f"SELECT * FROM {table} ORDER BY 1")))
        assert copied.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 0
        assert copied.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0] == 0


def test_incompatible_configuration_blocks_reset(installation, package, tmp_path):
    source = installation / "data/strumenti.db"
    with closing(sqlite3.connect(source)) as conn:
        conn.execute("ALTER TABLE users ADD COLUMN extra TEXT")
        conn.commit()
    manifest = deepcopy(package[0])
    manifest["database"].update(mode="reset", losses="Storico")
    with pytest.raises(ValueError, match="integralmente"):
        maintenance.prepare_database(source, tmp_path / "candidate.db", manifest)
    assert Database(source).get_user_by_username("admin") is not None


def test_admin_permission_and_cancel_reset(package, monkeypatch):
    SessionManager.logout()
    with pytest.raises(PermissionError):
        require_admin()
    SessionManager.set_user(SimpleNamespace(role="ADMIN"))
    manifest = deepcopy(package[0])
    manifest["database"].update(mode="reset", losses="Storico")
    dialog = SimpleNamespace(controller=SimpleNamespace(release=release_for(manifest)), _run=Mock())
    monkeypatch.setattr("src.gui.update_dialog.BASE_DIR", Path("fake-install"))
    monkeypatch.setattr("src.gui.update_dialog.messagebox.askyesno", lambda *args, **kwargs: False)
    try:
        UpdateDialog._install(dialog)
        dialog._run.assert_not_called()
    finally:
        SessionManager.logout()


def test_controller_notifies_once_and_keeps_errors_silent(monkeypatch, package):
    window = SimpleNamespace(after=Mock(return_value="timer"), after_cancel=Mock())
    controller = UpdateController(window)
    popup = Mock()
    monkeypatch.setattr("src.gui.update_dialog.messagebox.showwarning", popup)
    controller.events.put((None, "offline"))
    controller._poll()
    popup.assert_not_called()
    for _ in range(2):
        controller.events.put((release_for(package[0]), ""))
        controller._poll()
    assert popup.call_count == 1
    assert "operatore" in popup.call_args.args[1]


@pytest.mark.parametrize("failure", [None, "sync", "probe"])
def test_install_success_and_rollback(monkeypatch, installation, package, failure):
    job = stage(monkeypatch, installation, package)
    before = logical(installation / "data/strumenti.db")
    # Simula un file obsoleto che deve sparire soltanto se l'aggiornamento riesce.
    obsolete = installation / "src/obsolete.py"
    obsolete.write_text("old")

    def run(command, root, env):
        if command[1] == "sync":
            (root / ".venv/Scripts/python.exe").write_text("nuovo ambiente")
            if failure == "sync":
                raise RuntimeError("sync fallita")
        elif command[2] == "prepare":
            maintenance.prepare_database(Path(command[3]), Path(command[4]), json.loads(Path(command[5]).read_text()))
        elif failure == "probe":
            raise RuntimeError("avvio GUI fallito")

    monkeypatch.setattr(update_runner, "run_checked", run)
    assert update_runner.apply_update(installation, job, restart=False) == (failure is None)
    assert logical(installation / "data/strumenti.db") == before
    assert (job / "database.db").exists() and (job / "transcodifiche.txt").exists()
    assert (job / "transcodifiche.txt").read_text().strip()
    assert obsolete.exists() == (failure is not None)
    expected = "vecchio ambiente" if failure else "nuovo ambiente"
    assert (installation / ".venv/Scripts/python.exe").read_text() == expected


def test_interrupted_install_recovers_before_opening_database(monkeypatch, installation, package):
    job = stage(monkeypatch, installation, package)

    def power_failure(*args):
        raise RuntimeError("arresto simulato")

    monkeypatch.setattr(update_runner, "run_checked", power_failure)
    # Simula il processo terminato prima di poter eseguire il rollback.
    real_restore = update_runner.restore
    monkeypatch.setattr(update_runner, "restore", lambda *args: None)
    assert not update_runner.apply_update(installation, job, restart=False)
    (installation / "app.py").write_text("interrotto")
    monkeypatch.setattr(update_runner, "restore", real_restore)
    update_runner.recover(installation)
    assert (installation / "app.py").read_bytes() == (job / "previous/app.py").read_bytes()
    assert json.loads((installation / ".updates/active.json").read_text())["phase"] == "rolled_back"


def test_installer_exports_legacy_channels_before_migration(monkeypatch, installation, package):
    """Anche lo schema 0 senza sostanze produce il TXT prima della migrazione."""
    path = installation / "data/strumenti.db"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("DROP INDEX idx_transcodings_active_substance")
        conn.execute("ALTER TABLE transcodings DROP COLUMN lis_substance_code")
        conn.execute("PRAGMA user_version=0")
        conn.commit()
    job = stage(monkeypatch, installation, package)
    def run(command, root, env):
        if len(command) > 2 and command[2] == "prepare":
            maintenance.prepare_database(Path(command[3]), Path(command[4]), json.loads(Path(command[5]).read_text()))
    monkeypatch.setattr(update_runner, "run_checked", run)
    assert update_runner.apply_update(installation, job, restart=False)
    assert "Fluoruri:BG00594\n" in (job / "transcodifiche.txt").read_text(encoding="utf-8")
    with closing(sqlite3.connect(path)) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_second_instance_lock(tmp_path):
    first = update_runner.FileLock(tmp_path / "app.lock").acquire()
    try:
        with pytest.raises(RuntimeError, match="istanza"):
            update_runner.FileLock(tmp_path / "app.lock").acquire()
    finally:
        first.close()
