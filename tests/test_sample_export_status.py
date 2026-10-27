"""Stato campione basato sui soli risultati mappati, con dati sempre temporanei."""

from pathlib import Path

import pytest

from src.database import Database
from src.exporter import LISExporter
from src.models import ParsedResult, SampleFilter, SampleRecord


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Crea un database isolato per stato, merge e riallineamento all'avvio."""
    return Database(tmp_path / "status.db")


def result(name: str, mapped: bool = True, code: str | None = "STD") -> ParsedResult:
    """Costruisce un risultato con snapshot di mappatura esplicito."""
    return ParsedResult(name, "1.00", 1.0, "1,00", lis_exam_code=code, is_mapped=mapped)


def save_sample(db: Database, values: list[ParsedResult], number: int = 1) -> SampleRecord:
    """Salva e rilegge ID e flag effettivamente persistiti."""
    sample = SampleRecord(None, f"BG260010442001{number:04d}", "BG", 2026, "10442", 1, number, "test.csv")
    ok, message, sample_id = db.save_sample_with_results(sample, values)
    assert ok, message
    return db.get_sample_with_results(sample_id)


@pytest.mark.parametrize("mapped,code", [(False, None), (False, "IGNOTO"), (True, None), (True, "  ")])
def test_ignored_results_do_not_block_completion(db: Database, tmp_path: Path, mapped: bool, code: str | None):
    """Il campione è inviato quando il solo risultato esportabile è stato scritto."""
    sample = save_sample(db, [result("Configurato"), result("Ignorato", mapped, code)])
    assert sample.pending_results_count == 1
    assert db.get_samples()[0].pending_results_count == 1
    ok, _, output, count = LISExporter(db).export_samples([sample], tmp_path / "export", "sent.csv")
    assert ok and count == 1 and len(output.read_text().splitlines()) == 2
    saved = db.get_sample_with_results(sample.id)
    assert saved.status == "ESPORTATO" and saved.pending_results_count == 0
    assert saved.export_filename == "sent.csv" and saved.exported_at
    assert saved.results[0].is_exported and not saved.results[1].is_exported
    assert saved.results[1].exported_at is None
    assert db.get_samples(SampleFilter(status_filter="DA_ESPORTARE")) == []
    exported = db.get_samples(SampleFilter(status_filter="ESPORTATI"))
    assert len(exported) == 1 and exported[0].pending_results_count == 0
    assert db.get_summary_counts() == {"total": 1, "da_esportare": 0, "esportati": 1}


def test_unselected_mapped_result_still_blocks_completion(db: Database, tmp_path: Path):
    """I non mappati sono ignorati, ma i risultati mappati deselezionati restano pendenti."""
    sample = save_sample(db, [result("Primo"), result("Secondo"), result("Ignoto", False, None)])
    sample.results = sample.results[:1]
    assert LISExporter(db).export_samples([sample], tmp_path, "partial.csv")[0]
    partial = db.get_sample_with_results(sample.id)
    assert partial.status == "DA_ESPORTARE" and partial.pending_results_count == 1
    partial.results = partial.results[1:2]
    assert LISExporter(db).export_samples([partial], tmp_path, "final.csv")[0]
    complete = db.get_sample_with_results(sample.id)
    assert complete.status == "ESPORTATO" and complete.pending_results_count == 0
    assert [r.is_exported for r in complete.results] == [True, True, False]


def test_merge_unknown_does_not_reopen_but_new_mapping_does(db: Database, tmp_path: Path):
    """Un nuovo ignoto non riapre l'invio; configurarlo e reimportarlo lo rende pendente."""
    sample = save_sample(db, [result("Primo")])
    assert LISExporter(db).export_samples([sample], tmp_path, "first.csv")[0]
    sent = db.get_sample_with_results(sample.id)
    assert db.save_sample_with_results(sent, [result("Nuovo", False, None)], merge=True)[0]
    unchanged = db.get_sample_with_results(sample.id)
    assert unchanged.status == "ESPORTATO" and unchanged.pending_results_count == 0
    assert unchanged.export_filename == sent.export_filename and unchanged.exported_at == sent.exported_at
    assert db.save_sample_with_results(unchanged, [result("Nuovo", True, "NUOVO")], merge=True)[0]
    reopened = db.get_sample_with_results(sample.id)
    assert reopened.status == "DA_ESPORTARE" and reopened.pending_results_count == 1
    assert [r.is_exported for r in reopened.results] == [True, False]
    assert reopened.results[0].exported_at == sent.results[0].exported_at
    reopened.results = reopened.results[1:]
    assert LISExporter(db).export_samples([reopened], tmp_path, "second.csv")[0]
    assert db.get_sample_with_results(sample.id).status == "ESPORTATO"


def test_only_unmapped_remains_unsent_even_after_merge_and_restart(db: Database, tmp_path: Path):
    """Zero parametri pendenti non equivale a un invio mai avvenuto."""
    sample = save_sample(db, [result("Ignoto", False, None)])
    assert sample.pending_results_count == 0
    assert not LISExporter(db).export_samples([sample], tmp_path / "export")[0]
    assert db.save_sample_with_results(sample, [result("Altro ignoto", False, None)], merge=True)[0]
    reopened = Database(db.db_path)
    saved = reopened.get_sample_with_results(sample.id)
    assert saved.status == "DA_ESPORTARE" and saved.pending_results_count == 0
    assert saved.exported_at is None and saved.export_filename is None
    assert all(not r.is_exported for r in saved.results)


@pytest.mark.parametrize("existing_metadata", [False, True])
def test_startup_reconciliation_is_selective_and_idempotent(db: Database, existing_metadata: bool):
    """Riallinea il passato senza falsi invii, perdite di metadati o modifiche a ERRORE."""
    completed = save_sample(db, [result("Inviato"), result("Ignoto", False, None)], 1)
    pending = save_sample(db, [result("Inviato"), result("Pendente")], 2)
    unknown = save_sample(db, [result("Ignoto", False, None)], 3)
    error = save_sample(db, [result("Inviato"), result("Ignoto", False, None)], 4)
    real_time = "2026-10-20 10:20:30"
    with db.get_connection() as conn:
        for sample in (completed, pending, error):
            conn.execute("UPDATE sample_results SET is_exported=1, exported_at=? WHERE id=?",
                         (real_time, sample.results[0].id))
        conn.execute("UPDATE samples SET status='ERRORE' WHERE id=?", (error.id,))
        if existing_metadata:
            conn.execute("UPDATE samples SET exported_at='2026-10-19 09:00:00', export_filename='old.csv' WHERE id=?",
                         (completed.id,))
        version = conn.execute("PRAGMA user_version").fetchone()[0]
    before = {s.id: db.get_sample_results(s.id) for s in (completed, pending, unknown, error)}
    for _ in range(2):
        reopened = Database(db.db_path)
        saved = reopened.get_sample_with_results(completed.id)
        assert saved.status == "ESPORTATO" and saved.pending_results_count == 0
        assert saved.exported_at == ("2026-10-19 09:00:00" if existing_metadata else real_time)
        assert saved.export_filename == ("old.csv" if existing_metadata else None)
        assert reopened.get_sample_with_results(pending.id).status == "DA_ESPORTARE"
        assert reopened.get_sample_with_results(unknown.id).status == "DA_ESPORTARE"
        assert reopened.get_sample_with_results(error.id).status == "ERRORE"
        assert all(reopened.get_sample_results(s_id) == values for s_id, values in before.items())
        with reopened.get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM audit_logs WHERE action='SAMPLE_STATUS_RECONCILED'").fetchone()[0] == 1
            assert conn.execute("PRAGMA user_version").fetchone()[0] == version
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_gui_ignores_unmapped_in_pending_selection(db: Database, tmp_path: Path, ctk_root, monkeypatch: pytest.MonkeyPatch):
    """Il campione completato sparisce dai pendenti e non ripropone gli ignoti in Tutti."""
    from src.gui.master_detail import MasterDetailView

    sample = save_sample(db, [result("Configurato"), result("Ignoto", False, None)])
    db.save_config_value("path_export", str(tmp_path / "export"))
    for popup in ("showinfo", "showwarning", "showerror"):
        monkeypatch.setattr(f"src.gui.master_detail.messagebox.{popup}", lambda *args, **kw: None)
    view = MasterDetailView(ctk_root, db, db.get_user_by_username("admin"), lambda: None)
    try:
        assert view.selected_tests_by_sample[sample.id] == {sample.results[0].id}
        assert view.tree_detail.item(str(sample.results[1].id))["values"][1] == "⚪ Ignorato"
        view._handle_export_selected()
        assert db.get_sample_with_results(sample.id).status == "ESPORTATO"
        assert all(s.id != sample.id for s in view.loaded_samples)
        view.combo_status.set("Tutti")
        view._load_samples()
        assert view.selected_tests_by_sample[sample.id] == set()
        assert sample.id not in view.selected_sample_ids
        assert view.tree_master.item(str(sample.id))["values"][7] == "0/2"
    finally:
        view.destroy()
