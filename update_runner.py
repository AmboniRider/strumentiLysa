# SPDX-License-Identifier: AGPL-3.0-or-later
# Author: Amboni Paolo A.
"""Bootstrap e installatore esterno: usa solo la libreria standard Python.

Il journal viene scritto PRIMA delle modifiche. Un avvio successivo recupera
un'installazione interrotta prima di importare moduli o aprire il database.
"""

from __future__ import annotations

from contextlib import closing
from pathlib import Path
import json
import os
from pathlib import PurePosixPath
import shutil
import sqlite3
import subprocess
import sys
import time

ROOT_NAMES = {"app.py", "driver.py", "pyproject.toml", "uv.lock", "LICENSE",
              "strumenti.ico", "manuale.md", "progetto.md", "transfer.md",
              "update_runner.py", "maintenance.py", "UPDATES.md", "LEGAL.md", "strumenti.bat"}
_app_lock = None


class FileLock:
    """Lock esclusivo rilasciato dal sistema operativo anche dopo un arresto."""

    def __init__(self, path: Path):
        self.path = path
        self.stream = None

    def acquire(self, timeout: float = 0) -> "FileLock":
        """Acquisisce il lock o segnala un'altra istanza senza attesa illimitata."""
        self.stream = self.path.open("a+b")
        self.stream.seek(0, 2)
        if not self.stream.tell():
            self.stream.write(b"0")
            self.stream.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    self.close()
                    raise RuntimeError("Un'altra istanza o un aggiornamento è già in corso")
                time.sleep(0.1)

    def close(self) -> None:
        """Chiude l'handle e rilascia il lock senza cancellare il file condiviso."""
        if self.stream:
            self.stream.close()
            self.stream = None


def atomic_json(path: Path, data: dict) -> None:
    """Pubblica un journal completo: mai un JSON parzialmente scritto."""
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def checked_path(root: Path, name: str) -> Path:
    """Non permette al manifest di seguire link o uscire dall'installazione."""
    path = root / name
    if (path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or
            any(part.is_symlink() for part in path.parents if part != root.parent)):
        raise ValueError("Percorso aggiornamento non sicuro")
    return path


def runtime_name(name: str) -> bool:
    """Replica minima della whitelist per non importare codice sostituibile."""
    path = PurePosixPath(name)
    if (not name or "\\" in name or ":" in name or str(path) != name or
            any(part.startswith(".") or part == "__pycache__" for part in path.parts)):
        return False
    return name in ROOT_NAMES or (len(path.parts) > 1 and
            ((path.parts[0] == "src" and path.suffix == ".py") or
             (path.parts[0] == "driver_implementati" and path.suffix == ".md")))


def database_copy(source: Path, target: Path) -> None:
    """Snapshot completo incluso WAL; destinazione nuova obbligatoria."""
    with target.open("xb"):
        pass
    with closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original:
        with closing(sqlite3.connect(target)) as copied:
            deadline = time.monotonic() + 30

            def progress(status: int, remaining: int, total: int) -> None:
                if time.monotonic() > deadline:
                    raise TimeoutError("Database occupato")

            original.backup(copied, pages=128, progress=progress, sleep=0.1)
            if copied.execute("PRAGMA integrity_check").fetchall() != [("ok",)] or copied.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Backup database non valido")


def restore(root: Path, job: Path, state: dict) -> None:
    """Ripristino ripetibile: gli originali restano disponibili anche se interrotto."""
    for name, existed in state["originals"].items():
        target = checked_path(root, name)
        if existed:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + ".restore")
            shutil.copy2(job / "previous" / name, temporary)
            os.replace(temporary, target)
        else:
            target.unlink(missing_ok=True)
    # Questa copia viene ripristinata solo se la sostituzione era iniziata.
    if state.get("database_started"):
        target = root / "data/strumenti.db"
        for suffix in ("-wal", "-shm"):
            Path(str(target) + suffix).unlink(missing_ok=True)
        temporary = target.with_suffix(".restore")
        shutil.copy2(job / "database.db", temporary)
        os.replace(temporary, target)
    if state.get("environment_started"):
        previous = job / "previous-env"
        if previous.exists():
            # Non rinominiamo il backup: anche un secondo ripristino è possibile.
            if (root / ".venv").exists():
                shutil.rmtree(root / ".venv")
            shutil.copytree(previous, root / ".venv")
    state["phase"] = "rolled_back"
    atomic_json(root / ".updates/active.json", state)


def recover(root: Path) -> None:
    """Recupera prima del login un aggiornamento interrotto a metà."""
    journal = root / ".updates/active.json"
    if not journal.exists():
        return
    state = json.loads(journal.read_text(encoding="utf-8"))
    job = checked_path(root, state["job"])
    if state["phase"] in ("applying", "validating"):
        restore(root, job, state)
        atomic_json(root / ".updates/last-result.json", {"message": "Aggiornamento interrotto: versione precedente ripristinata.\nBackup e transcodifiche: " + str(job), "reported": False})


def bootstrap(root: Path) -> None:
    """Esclude altre istanze e recupera l'installazione prima degli import GUI."""
    global _app_lock
    guard = FileLock(root / ".update.lock").acquire()
    try:
        _app_lock = FileLock(root / ".app.lock").acquire()
        journal = root / ".updates/active.json"
        if journal.exists() and json.loads(journal.read_text(encoding="utf-8"))["phase"] in ("applying", "validating"):
            # Il Python della .venv non può rimuovere il proprio eseguibile su
            # Windows. Delegare al runtime base permette un recupero completo.
            state = json.loads(journal.read_text(encoding="utf-8"))
            job = checked_path(root, state["job"])
            subprocess.Popen([getattr(sys, "_base_executable", sys.executable), str(job / "runner.py"),
                              str(root), str(job), "--recover"], cwd=root,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            _app_lock.close()
            raise SystemExit(0)
    finally:
        guard.close()


def apply_update(root: Path, job: Path, restart: bool = True) -> bool:
    """Installa con journal, copia conservativa e rollback su qualunque errore."""
    guard = FileLock(root / ".update.lock").acquire()
    app_lock = FileLock(root / ".app.lock")
    state = None
    try:
        app_lock.acquire(timeout=60)
        if (root / ".git").exists():
            raise RuntimeError("Aggiornamento automatico vietato nelle copie Git")
        manifest = json.loads((job / "manifest.json").read_text(encoding="utf-8"))
        if not all(runtime_name(name) for name in manifest["files"]):
            raise ValueError("Il manifest tenta di modificare file non gestiti")
        # Il runner riceve un job locale già verificato; ricontrolliamo i file
        # prima di toccare il runtime per rilevare modifiche dopo il download.
        import hashlib
        for name, digest in manifest["files"].items():
            checked_path(root, name)
            if hashlib.sha256((job / "payload" / name).read_bytes()).hexdigest() != digest:
                raise ValueError("Payload modificato dopo la verifica")
        database_copy(root / "data/strumenti.db", job / "database.db")
        # Un TXT compatibile è sempre disponibile anche se il nuovo schema fallisce.
        with closing(sqlite3.connect(job / "database.db")) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(transcodings)")}
            substance = "lis_substance_code" if "lis_substance_code" in columns else "NULL"
            rows = conn.execute(f"SELECT instrument_param_name, lis_exam_code, {substance} FROM transcodings ORDER BY id").fetchall()
        text = "".join(":".join(str(v) for v in row if v is not None) + "\n" for row in rows)
        (job / "transcodifiche.txt").write_text(text, encoding="utf-8")
        managed = set(manifest["files"]) | {name for name in ROOT_NAMES if (root / name).is_file()}
        managed.update(p.relative_to(root).as_posix() for p in (root / "src").rglob("*.py"))
        managed.update(p.relative_to(root).as_posix() for p in (root / "driver_implementati").glob("*.md"))
        originals = {}
        for name in sorted(managed):
            original = checked_path(root, name)
            originals[name] = original.is_file()
            if originals[name]:
                target = job / "previous" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, target)
        # Copiare l'ambiente mantiene intatta la posizione dei suoi eseguibili.
        # Solo dopo una copia completa si autorizza qualunque modifica al runtime.
        if not (root / ".venv").is_dir():
            raise RuntimeError("Ambiente locale mancante")
        required = ((job / "database.db").stat().st_size * 2 +
                    sum(p.stat().st_size for p in (root / ".venv").rglob("*") if p.is_file()) * 2 +
                    300 * 1024 * 1024)
        if shutil.disk_usage(root).free < required:
            raise RuntimeError("Spazio insufficiente per conservare ambiente e database precedenti")
        shutil.copytree(root / ".venv", job / "previous-env")
        state = {"job": job.relative_to(root).as_posix(), "phase": "applying", "originals": originals,
                 "database_started": False, "environment_started": False}
        atomic_json(root / ".updates/active.json", state)
        for name in managed:
            target = checked_path(root, name)
            source = job / "payload" / name
            if source.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + ".update")
                shutil.copy2(source, temporary)
                os.replace(temporary, target)
            else:
                target.unlink(missing_ok=True)
        # Non lasciare bytecode del vecchio programma con timestamp coincidenti.
        for cache in (root / "src").rglob("__pycache__"):
            shutil.rmtree(cache)
        state["environment_started"] = True
        atomic_json(root / ".updates/active.json", state)
        env = os.environ.copy()
        env.update(UV_PROJECT_ENVIRONMENT=str(root / ".venv"), VIRTUAL_ENV="",
                   UV_CACHE_DIR=str(root / ".uv-cache"), UV_PYTHON_INSTALL_DIR=str(root / ".runtime/python"))
        run_checked([str(root / ".tools/uv.exe"), "sync", "--locked", "--no-dev", "--no-install-project",
                     "--python", sys.executable], root, env)
        python = root / ".venv/Scripts/python.exe"
        candidate = job / "candidate.db"
        run_checked([str(python), "maintenance.py", "prepare", str(job / "database.db"), str(candidate),
                     str(job / "manifest.json")], root, env)
        state["database_started"] = True
        atomic_json(root / ".updates/active.json", state)
        database = root / "data/strumenti.db"
        for suffix in ("-wal", "-shm"):
            Path(str(database) + suffix).unlink(missing_ok=True)
        os.replace(candidate, database)
        state["phase"] = "validating"
        atomic_json(root / ".updates/active.json", state)
        run_checked([str(python), "maintenance.py", "probe", str(database), manifest["version"]], root, env)
        state["phase"] = "complete"
        atomic_json(root / ".updates/active.json", state)
        (job / "result.txt").write_text("Aggiornamento completato. Backup: " + str(job / "database.db"), encoding="utf-8")
        atomic_json(root / ".updates/last-result.json", {"message": "Aggiornamento completato.\nBackup e transcodifiche: " + str(job), "reported": False})
        return True
    except BaseException as exc:
        if state is not None:
            restore(root, job, state)
        (job / "result.txt").write_text("Aggiornamento non completato; versione precedente conservata/ripristinata.\n" + str(exc), encoding="utf-8")
        atomic_json(root / ".updates/last-result.json", {"message": "Aggiornamento non completato; versione precedente conservata/ripristinata.\nDettagli e copie: " + str(job), "reported": False})
        return False
    finally:
        app_lock.close()
        guard.close()
        if restart:
            # Il launcher imposta i percorsi uv come nell'installazione originale.
            subprocess.Popen(["cmd.exe", "/c", str(root / "strumenti.bat")], cwd=root,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def run_checked(command: list[str], root: Path, env: dict) -> None:
    """Timeout finito e log locale senza includere contenuti delle tabelle."""
    result = subprocess.run(command, cwd=root, env=env, capture_output=True, text=True, timeout=300)
    if result.returncode:
        raise RuntimeError("Comando di aggiornamento fallito: " + " ".join(command[:2]) + "\n" + result.stderr[-2000:])


def main() -> None:
    """Entry point del runner copiato nella cartella privata dell'aggiornamento."""
    title = "STRUMENTI LYSA - AGGIORNAMENTO"
    if os.name == "nt":
        import ctypes
        ctypes.windll.kernel32.SetConsoleTitleW(title)
    print(f"\033]0;{title}\007\n\033[93m+========================================+\n| \033[96m{title}\033[93m |\n+========================================+\033[0m")
    if sys.argv[1] == "recover-only":
        root = Path(__file__).resolve().parent
        guard = FileLock(root / ".update.lock").acquire()
        lock = FileLock(root / ".app.lock").acquire()
        try:
            recover(root)
        finally:
            lock.close()
            guard.close()
        return
    root, job = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if not job.is_relative_to(root / ".updates"):
        raise ValueError("Job non valido")
    if "--recover" in sys.argv:
        guard = FileLock(root / ".update.lock").acquire(timeout=60)
        lock = FileLock(root / ".app.lock").acquire(timeout=60)
        try:
            recover(root)
        finally:
            lock.close()
            guard.close()
        subprocess.Popen(["cmd.exe", "/c", str(root / "strumenti.bat")], cwd=root,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        raise SystemExit(0 if apply_update(root, job, restart="--no-restart" not in sys.argv) else 1)


if __name__ == "__main__":
    main()
