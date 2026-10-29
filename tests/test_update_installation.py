"""Collaudo Windows reale su copia isolata, attivabile esplicitamente."""

from contextlib import closing
import json
import os
import platform
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

import pytest

import build_release
import trasfer
from src import __version__
from src.database import Database
from src.update_service import Release, stage_release
import src.update_service as service


@pytest.mark.skipif(os.name != "nt" or os.getenv("STRUMENTI_UPDATE_E2E") != "1",
                    reason="Impostare STRUMENTI_UPDATE_E2E=1 per il collaudo Windows isolato")
@pytest.mark.parametrize("intranet", [False, True])
def test_real_windows_install_update_offline_and_recovery(tmp_path: Path, monkeypatch, intranet: bool):
    """Esegue vero uv, runner esterno, GUI nascosta e recupero senza Git/rete."""
    root = tmp_path / "PC installato con spazi è"
    root.mkdir()
    for name in trasfer.RUNTIME_FILES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(trasfer.PROJECT_ROOT / name, target)
    shutil.copytree(Path(sys.prefix), root / ".venv")
    (root / ".tools").mkdir()
    shutil.copyfile(shutil.which("uv"), root / ".tools/uv.exe")
    (root / "strumenti.bat").write_text(trasfer.launcher_batch(), encoding="utf-8")
    old_init = root / "src/__init__.py"
    old_init.write_text(old_init.read_text(encoding="utf-8").replace(f'__version__ = "{__version__}"', '__version__ = "1.1.0"'), encoding="utf-8")
    db = Database(root / "data/strumenti.db")
    assert db.update_user_password(1, "password-collaudo")[0]
    db.save_config_value("allowed_labs", "BG")
    db.save_transcoding("Canale prova", "ESAME123", "descrizione", "00500")
    with db.get_connection() as conn:
        conn.execute("INSERT INTO samples (sample_code,lab_code,year,acceptance,conferment,sample_number,source_filename) VALUES ('BG2600104430010001','BG',26,'10443',1,1,'prova.txt')")
        conn.execute("INSERT INTO sample_results (sample_id,param_name,raw_value,formatted_value) VALUES (1,'Canale prova','1','1,0')")
        conn.execute("INSERT INTO audit_logs (username,action) VALUES ('admin','TEST')")
    with closing(sqlite3.connect(db.db_path)) as conn:
        before = "\n".join(conn.iterdump())
    manifest_path = build_release.build_release(trasfer.PROJECT_ROOT, tmp_path / "release")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload = next(manifest_path.parent.glob("*.zip")).read_bytes()
    monkeypatch.setattr(service, "download", lambda *args: payload)
    if intranet:
        from src.intranet_updates import check_intranet_release
        distribution = os.getenv("STRUMENTI_INTRANET_E2E_RELEASE")
        if not distribution:
            pytest.skip("Impostare STRUMENTI_INTRANET_E2E_RELEASE alla distribuzione offline reale")
        release = check_intranet_release("1.1.0", Path(distribution))
        manifest = release.manifest
        job = stage_release(release, root, 1)
        # Cache nuova e vuota: l'esito non può dipendere dal PC di sviluppo.
        (root / ".uv-cache").mkdir()
    else:
        job = stage_release(Release(manifest["version"], "", "", manifest), root, 1)
    base = getattr(sys, "_base_executable", sys.executable)
    env = os.environ.copy()
    env.update(UV_OFFLINE="1", PYTHONPATH="")
    result = subprocess.run([base, str(job / "runner.py"), str(root), str(job), "--no-restart"],
                            cwd=root, env=env, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, (job / "result.txt").read_text(encoding="utf-8") + result.stderr
    assert not (root / ".git").exists()
    with closing(sqlite3.connect(db.db_path)) as conn:
        assert "\n".join(conn.iterdump()) == before
    smoke = """
import sys
from pathlib import Path
from update_runner import bootstrap
bootstrap(Path.cwd())
from src import __version__
from src.auth import verify_password
from src.database import Database
from src.gui.app_window import AppWindow
from tkinter import messagebox
messagebox.showinfo = lambda *a, **k: None
db = Database()
user = db.get_user_by_username('admin')
assert verify_password('password-collaudo', user.password_hash, user.salt)
assert db.get_transcoding_map()['Canale prova'] == 'ESAME123'
assert __version__ == sys.argv[1]
app = AppWindow(db, check_updates=False)
app.withdraw()
app.show_dashboard(user)
assert app.current_view.loaded_samples
app.after(300, app.destroy)
app.mainloop()
print('LOGIN_DATI_GUI_OFFLINE_OK')
"""
    result = subprocess.run([str(root / ".venv/Scripts/python.exe"), "-c", smoke, manifest["version"]], cwd=root, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0 and "LOGIN_DATI_GUI_OFFLINE_OK" in result.stdout, result.stderr
    journal = root / ".updates/active.json"
    state = json.loads(journal.read_text(encoding="utf-8"))
    state["phase"] = "applying"
    journal.write_text(json.dumps(state), encoding="utf-8")
    # Il bootstrap base deve ripristinare anche se il Python virtuale è perso.
    (root / ".venv/Scripts/python.exe").unlink()
    result = subprocess.run([base, str(root / "update_runner.py"), "recover-only"], cwd=root, env=env,
                            capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert (root / ".venv/Scripts/python.exe").exists()
    assert '"1.1.0"' in old_init.read_text(encoding="utf-8")
    assert json.loads(journal.read_text(encoding="utf-8"))["phase"] == "rolled_back"
    # Esegue anche il bootstrap BAT reale, da un percorso con spazi e con uv
    # locale. La riga di avvio GUI è sostituita solo nel BAT di collaudo: la GUI
    # vera è già stata esercitata sopra senza richiedere interazione umana.
    managed = root / ".runtime/python" / f"cpython-{platform.python_version()}-windows-x86_64-none"
    shutil.copytree(Path(base).parent, managed)
    batch = trasfer.launcher_batch().replace('".tools\\uv.exe" run --no-sync --offline python app.py', 'echo BOOTSTRAP_BAT_OK')
    check_batch = root / "verifica launcher.bat"
    check_batch.write_text(batch.replace("\n", "\r\n"), encoding="utf-8", newline="")
    result = subprocess.run(["cmd.exe", "/c", str(check_batch)], cwd=root, env=env, input="\n",
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0 and "BOOTSTRAP_BAT_OK" in result.stdout, result.stdout + result.stderr
