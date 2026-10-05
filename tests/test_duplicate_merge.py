"""Test per l'unione intelligente (Merge) dei campioni duplicati e tracciamento LIS per parametro."""

from pathlib import Path
import sqlite3
import customtkinter as ctk
import pytest

from src.database import Database
from src.exporter import LISExporter
from src.gui.master_detail import MasterDetailView
from src.models import ParsedResult, SampleRecord, UserRecord


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    """Fixture per istanziare un database SQLite di test isolato."""
    db_file = tmp_path / "test_merge.db"
    return Database(db_file)


@pytest.fixture
def admin_user() -> UserRecord:
    return UserRecord(
        id=1,
        username="admin",
        password_hash="hash",
        salt="salt",
        role="ADMIN",
    )



def test_merge_duplicate_sample_adds_new_tests(test_db: Database):
    """Verifica che il merge aggiunga nuovi parametri ad un campione esistente e aggiorni quelli esistenti."""
    s = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="first_run.txt",
    )
    initial_results = [
        ParsedResult(param_name="Cloruro", raw_value="10,0", numeric_value=10.0, formatted_value="10,0", lis_exam_code="BG001", is_mapped=True),
        ParsedResult(param_name="Nitrato", raw_value="5,0", numeric_value=5.0, formatted_value="5,0", lis_exam_code="BG002", is_mapped=True),
    ]
    ok, _, sample_id = test_db.save_sample_with_results(s, initial_results)
    assert ok is True
    assert sample_id is not None

    # Secondo invio dello stesso campione con Nitrato aggiornato e Solfato nuovo
    s2 = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="second_run.txt",
    )
    second_results = [
        ParsedResult(param_name="Nitrato", raw_value="6,5", numeric_value=6.5, formatted_value="6,5", lis_exam_code="BG002", is_mapped=True),
        ParsedResult(param_name="Solfato", raw_value="20,0", numeric_value=20.0, formatted_value="20,0", lis_exam_code="BG003", is_mapped=True),
    ]
    ok2, msg2, sample_id2 = test_db.save_sample_with_results(s2, second_results, merge=True)
    assert ok2 is True
    assert sample_id2 == sample_id
    assert "+1 nuovi test" in msg2

    # Verifica stato e risultati nel DB
    reloaded = test_db.get_sample_with_results(sample_id)
    assert reloaded is not None
    assert reloaded.results_count == 3
    assert reloaded.status == "DA_ESPORTARE"

    r_map = {r.param_name: r for r in reloaded.results}
    assert "Cloruro" in r_map
    assert "Nitrato" in r_map
    assert "Solfato" in r_map

    # Cloruro invariato
    assert r_map["Cloruro"].formatted_value == "10,0"
    # Nitrato aggiornato con il nuovo valore
    assert r_map["Nitrato"].formatted_value == "6,5"
    # Solfato inserito correttamente
    assert r_map["Solfato"].formatted_value == "20,0"
    assert r_map["Solfato"].is_exported is False


def test_merge_preserves_already_exported_status(test_db: Database, tmp_path: Path):
    """Verifica che se un campione era già ESPORTATO, i nuovi test lo riaprano a DA_ESPORTARE ma i vecchi test rimangano is_exported=True."""
    exporter = LISExporter(test_db)
    s = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="run1.txt",
    )
    res_list = [
        ParsedResult(param_name="Cloruro", raw_value="10,0", numeric_value=10.0, formatted_value="10,0", lis_exam_code="BG001", is_mapped=True),
    ]
    _, _, sample_id = test_db.save_sample_with_results(s, res_list)
    assert sample_id is not None

    sample_full = test_db.get_sample_with_results(sample_id)
    assert sample_full is not None

    # Esporta la prima analisi al LIS
    out_dir = tmp_path / "exp"
    ok, _, _, count = exporter.export_samples([sample_full], out_dir, "EXP_1.csv")
    assert ok is True
    assert count == 1

    reloaded_exported = test_db.get_sample_with_results(sample_id)
    assert reloaded_exported is not None
    assert reloaded_exported.status == "ESPORTATO"
    assert reloaded_exported.results[0].is_exported is True

    # Ora arriva una seconda analisi per lo stesso campione con un nuovo test (pH) e Cloruro rianalizzato
    s_new = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="run2.txt",
    )
    new_results = [
        ParsedResult(param_name="Cloruro", raw_value="11,2", numeric_value=11.2, formatted_value="11,2", lis_exam_code="BG001", is_mapped=True),
        ParsedResult(param_name="PH", raw_value="7,4", numeric_value=7.4, formatted_value="7,4", lis_exam_code="BG00598", is_mapped=True),
    ]
    ok_merge, _, _ = test_db.save_sample_with_results(s_new, new_results, merge=True)
    assert ok_merge is True

    # Verifica che il campione sia tornato DA_ESPORTARE
    reloaded_merged = test_db.get_sample_with_results(sample_id)
    assert reloaded_merged is not None
    assert reloaded_merged.status == "DA_ESPORTARE"
    assert reloaded_merged.results_count == 2
    assert reloaded_merged.pending_results_count == 1

    r_map = {r.param_name: r for r in reloaded_merged.results}
    # Cloruro ha il nuovo valore ma rimane is_exported=True (scelta concordata via grill-me)
    assert r_map["Cloruro"].formatted_value == "11,2"
    assert r_map["Cloruro"].is_exported is True
    # PH è nuovo e non ancora esportato
    assert r_map["PH"].is_exported is False

    # Seconda esportazione: selezionando solo i test non esportati (comportamento predefinito)
    pending_only = [r for r in reloaded_merged.results if not r.is_exported]
    reloaded_merged.results = pending_only
    ok_exp2, _, out_file2, count2 = exporter.export_samples([reloaded_merged], out_dir, "EXP_2.csv")
    assert ok_exp2 is True
    assert count2 == 1

    # Verifica contenuto secondo file: contiene SOLO il nuovo test PH
    lines2 = out_file2.read_text(encoding="utf-8").splitlines()
    assert len(lines2) == 2  # header + 1 riga
    assert "BG00598" in lines2[1]
    assert "BG001" not in lines2[1]

    # Ora il campione torna definitivamente a ESPORTATO
    final_sample = test_db.get_sample_with_results(sample_id)
    assert final_sample is not None
    assert final_sample.status == "ESPORTATO"
    assert all(r.is_exported for r in final_sample.results)


def test_schema_migration_auto_adds_columns(tmp_path: Path):
    """Verifica che la migrazione aggiunga le colonne is_exported ed exported_at a un DB SQLite creato con vecchio schema."""
    db_file = tmp_path / "legacy.db"

    # Crea tabella con il vecchio schema (senza is_exported ed exported_at)
    conn = sqlite3.connect(db_file)
    conn.execute("""
        CREATE TABLE samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_code TEXT UNIQUE NOT NULL,
            lab_code TEXT NOT NULL,
            year INTEGER NOT NULL,
            acceptance TEXT NOT NULL,
            conferment INTEGER NOT NULL,
            sample_number INTEGER NOT NULL,
            source_filename TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'DA_ESPORTARE',
            imported_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            exported_at DATETIME,
            export_filename TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE sample_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sample_id INTEGER NOT NULL REFERENCES samples(id) ON DELETE CASCADE,
            param_name TEXT NOT NULL,
            raw_value TEXT NOT NULL,
            numeric_value REAL,
            formatted_value TEXT NOT NULL,
            lis_exam_code TEXT,
            is_mapped INTEGER DEFAULT 1
        )
    """)
    # Inserisci un campione già ESPORTATO
    conn.execute("""
        INSERT INTO samples (sample_code, lab_code, year, acceptance, conferment, sample_number, source_filename, status)
        VALUES ('BG2600104420010001', 'BG', 2026, '10442', 1, 1, 'old.txt', 'ESPORTATO')
    """)
    s_id = conn.execute("SELECT id FROM samples").fetchone()[0]
    conn.execute("""
        INSERT INTO sample_results (sample_id, param_name, raw_value, numeric_value, formatted_value, lis_exam_code)
        VALUES (?, 'Cloruri', '1,0', 1.0, '1,0', 'BG001')
    """, (s_id,))
    conn.commit()
    conn.close()

    # Istanzia la classe Database sul file legacy: deve migrare automaticamente
    migrated_db = Database(db_file)

    # Verifica presenza colonne
    with migrated_db.get_connection() as c:
        info = [row["name"] for row in c.execute("PRAGMA table_info(sample_results)").fetchall()]
        assert "is_exported" in info
        assert "exported_at" in info

        # Verifica che il record del campione già esportato abbia is_exported = 1
        res = c.execute("SELECT is_exported FROM sample_results WHERE sample_id = ?", (s_id,)).fetchone()
        assert res["is_exported"] == 1


def test_gui_detail_table_shows_status_lis(ctk_root, test_db: Database, admin_user: UserRecord):
    """Verifica che la tabella di dettaglio della GUI mostri la colonna Stato LIS e pre-selezioni solo i test da inviare."""
    s = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="test.txt",
    )
    results = [
        ParsedResult(param_name="ParamInviato", raw_value="1,0", numeric_value=1.0, formatted_value="1,0", lis_exam_code="BG001", is_mapped=True),
        ParsedResult(param_name="ParamDaInviare", raw_value="2,0", numeric_value=2.0, formatted_value="2,0", lis_exam_code="BG002", is_mapped=True),
    ]
    _, _, sample_id = test_db.save_sample_with_results(s, results)
    assert sample_id is not None

    # Simula che il primo test sia già stato esportato
    res_list = test_db.get_sample_results(sample_id)
    test_db.mark_results_as_exported([res_list[0].id], [sample_id], "TEST.csv")

    view = MasterDetailView(master=ctk_root, db=test_db, current_user=admin_user, on_logout=lambda: None)
    view.update_idletasks()

    # Verifica che le colonne di dettaglio includano status_lis
    cols = view.tree_detail["columns"]
    assert "status_lis" in cols

    # Verifica righe nel dettaglio
    children = view.tree_detail.get_children()
    assert len(children) == 2

    row0 = view.tree_detail.item(children[0])["values"]
    row1 = view.tree_detail.item(children[1])["values"]

    # riga 0: ParamInviato -> deselezionato [ ] e stato 🟢 Inviato
    assert row0[0] == " [  ] "
    assert row0[1] == "🟢 Inviato"

    # riga 1: ParamDaInviare -> selezionato [✓] e stato 🟠 Da Inviare
    assert row1[0] == " [✓] "
    assert row1[1] == "🟠 Da Inviare"
