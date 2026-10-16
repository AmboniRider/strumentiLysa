"""Regressioni per sostanze LIS, migrazione, invii completi e interfaccia.

Tutti i database e i file strumentali sono sintetici e confinati a tmp_path;
il CSV fornito viene soltanto letto come riferimento del tracciato.
"""

import csv
from pathlib import Path
import sqlite3
import subprocess
import sys
from tkinter import messagebox

import customtkinter as ctk
import pytest

from driver import DionexICDriver, MettlerToledoDriver, SpectrophotometerDriver
from src.auth import SessionManager
from src.config import AppConfig
from src.database import Database
from src.exporter import LIS_CSV_HEADER, LISExporter
from src.gui.master_detail import MasterDetailView
from src.gui.settings_dialog import SettingsDialog
from src.importer_service import ImporterService
from src.models import ParsedResult, SampleRecord


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Crea uno schema isolato con le transcodifiche standard iniziali."""
    return Database(tmp_path / "substances.db")


def result(name: str, substance: str | None = None, value: str = "50,60",
           exam: str = "BG00611") -> ParsedResult:
    """Costruisce una misura mantenendo la precisione del testo originale."""
    return ParsedResult(name, value, float(value.replace(",", ".")), value,
                        lis_exam_code=exam, is_mapped=True, lis_substance_code=substance)


def save_sample(db: Database, results: list[ParsedResult], code: str = "BG2600104420010001") -> SampleRecord:
    """Salva un campione e restituisce i risultati con i loro ID reali."""
    sample = SampleRecord(None, code, "BG", 2026, "10442", 1, 1, "synthetic.txt")
    ok, message, sample_id = db.save_sample_with_results(sample, results)
    assert ok, message
    saved = db.get_sample_with_results(sample_id)
    assert saved is not None
    return saved


def catalog(db: Database) -> None:
    """Configura un esame sintetico con due sostanze obbligatorie."""
    for name, code in (("Uno", "00500"), ("Due", "a002")):
        ok, message = db.save_transcoding(name, "BG00611", lis_substance_code=code)
        assert ok, message


def read_export(path: Path) -> list[dict[str, str]]:
    """Legge l'export reale con il separatore LIS conservato."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=";")
        assert reader.fieldnames == LIS_CSV_HEADER
        return list(reader)


def test_migration_preserves_legacy_results_and_is_repeatable(tmp_path: Path):
    """Un database precedente conserva ID, codici, valori e stato di invio."""
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE transcodings (
                id INTEGER PRIMARY KEY, instrument_param_name TEXT UNIQUE COLLATE NOCASE,
                lis_exam_code TEXT, description TEXT, is_active INTEGER DEFAULT 1,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP);
            INSERT INTO transcodings VALUES (91, 'Storico', 'STD', 'originale', 1, '2026-01-01');
            CREATE TABLE samples (
                id INTEGER PRIMARY KEY, sample_code TEXT UNIQUE, lab_code TEXT,
                year INTEGER, acceptance TEXT, conferment INTEGER, sample_number INTEGER,
                source_filename TEXT, status TEXT, imported_at DATETIME,
                exported_at DATETIME, export_filename TEXT);
            INSERT INTO samples VALUES (23, 'BG2600104420010001', 'BG', 2026, '10442',
                1, 1, 'originale.txt', 'ESPORTATO', '2026-01-01', '2026-01-02', 'old.csv');
            CREATE TABLE sample_results (
                id INTEGER PRIMARY KEY, sample_id INTEGER REFERENCES samples(id),
                param_name TEXT, raw_value TEXT, numeric_value REAL, formatted_value TEXT,
                lis_exam_code TEXT, is_mapped INTEGER, is_exported INTEGER, exported_at DATETIME);
            INSERT INTO sample_results VALUES
                (45, 23, 'Storico', '1,20', 1.2, '1,20', 'STD', 1, 1, '2026-01-02');
        """)
    migrated = Database(path)
    sample = migrated.get_sample_with_results(23)
    assert sample.status == "ESPORTATO" and sample.export_filename == "old.csv"
    assert sample.results[0].id == 45
    assert sample.results[0].lis_substance_code is None
    assert sample.results[0].is_exported and sample.results[0].exported_at == "2026-01-02"
    assert sample.results[0].formatted_value == "1,20"
    rule = migrated.get_transcoding_by_id(91)
    assert rule.description == "originale" and rule.lis_substance_code is None
    assert migrated.save_transcoding("Nuova", "BG00611", lis_substance_code="00500")[0]
    migrated.init_db()
    assert migrated.get_transcoding_rules_map()["Nuova"].lis_substance_code == "00500"
    assert migrated.get_sample_with_results(23) == sample


def test_crud_and_database_constraint_preserve_codes(db: Database):
    """CRUD e indice parziale impediscono coppie concorrenti, lasciando liberi gli standard."""
    catalog(db)
    one = db.get_transcoding_rules_map()["Uno"]
    assert db.get_transcoding_map()["Uno"] == "BG00611"
    assert db.update_transcoding(one.id, "Uno", "BG00611", "descrizione", " 00500 ")[0]
    assert db.get_transcoding_by_id(one.id).lis_substance_code == "00500"
    assert not db.save_transcoding("Alias", "BG00611", lis_substance_code="00500")[0]
    two = db.get_transcoding_rules_map()["Due"]
    assert not db.update_transcoding(two.id, "Due", "BG00611", lis_substance_code="00500")[0]
    assert db.get_transcoding_by_id(two.id).lis_substance_code == "a002"
    assert not db.save_transcoding("Invalid", "BG00611", lis_substance_code="50;00")[0]
    with pytest.raises(sqlite3.IntegrityError), db.get_connection() as conn:
        conn.execute("""INSERT INTO transcodings (instrument_param_name, lis_exam_code, lis_substance_code)
                        VALUES ('Bypass', 'BG00611', '00500')""")
    with db.get_connection() as conn:
        conn.execute("UPDATE transcodings SET is_active=0 WHERE id=?", (one.id,))
    assert db.save_transcoding("Alias", "BG00611", lis_substance_code="00500")[0]
    assert not db.save_transcoding("Uno", "BG00611", lis_substance_code="00500")[0]
    assert db.save_transcoding("StandardUno", "STD")[0]
    assert db.save_transcoding("StandardDue", "STD", lis_substance_code=" ")[0]


@pytest.mark.parametrize("invalid", [
    "Nuova:STD\nmalformata", "Nuova:STD\nnuova:ALT", "Nuova:STD\nAlias:BG00611:00500",
    "Nuova:BG00611:ABC\nAltra:BG00611:ABC", "Nuova:STD\nAltra:BG00611:a-b",
])
def test_txt_invalid_import_is_atomic(db: Database, invalid: str):
    """Anche errori nell'ultima riga lasciano intatte tutte le regole."""
    catalog(db)
    before = db.get_all_transcodings()
    ok, message = db.import_transcodings_text(invalid)
    assert not ok and "Nessuna regola importata" in message
    assert db.get_all_transcodings() == before


def test_txt_roundtrip_clear_substance_and_swap_targets(db: Database, tmp_path: Path):
    """Il TXT conserva i codici, permette scambi atomici e rende standard le righe a due campi."""
    catalog(db)
    exported = db.export_transcodings_text()
    assert "Uno:BG00611:00500\n" in exported and "Due:BG00611:a002\n" in exported
    other = Database(tmp_path / "roundtrip.db")
    assert other.import_transcodings_text(exported)[0]
    assert other.export_transcodings_text() == exported
    assert db.import_transcodings_text("Uno:BG00611:a002\nDue:BG00611:00500")[0]
    assert db.get_transcoding_rules_map()["Uno"].lis_substance_code == "a002"
    assert db.import_transcodings_text("Uno:BG00611")[0]
    assert db.get_transcoding_rules_map()["Uno"].lis_substance_code is None


def test_txt_write_failure_rolls_back_prior_updates(db: Database):
    """Un errore SQLite dopo la prima scrittura ripristina valori e attivazione."""
    catalog(db)
    before = db.get_all_transcodings()
    with db.get_connection() as conn:
        conn.execute("""CREATE TRIGGER reject_rule BEFORE INSERT ON transcodings
                        WHEN NEW.instrument_param_name='Rifiuta'
                        BEGIN SELECT RAISE(ABORT, 'errore simulato'); END""")
    assert not db.import_transcodings_text("Uno:BG00611:NEW\nRifiuta:STD")[0]
    assert db.get_all_transcodings() == before


@pytest.mark.parametrize("instrument", [DionexICDriver, SpectrophotometerDriver, MettlerToledoDriver])
def test_importer_snapshot_and_reimport_all_drivers(db: Database, tmp_path: Path, instrument):
    """Il servizio arricchisce tutti i driver e cambia i codici solo alla reimportazione."""
    catalog(db)
    code = "BG2600104420010001"
    if instrument is DionexICDriver:
        text = f"Sample Name:\t{code}\nComponent\tAmount\nUno\t50.60\nDue\tn.a.\n"
    elif instrument is SpectrophotometerDriver:
        text = "# UV-Vis\nParametro;Valore\nUno;50.60\nDue;n.a.\n"
    else:
        text = f"Report\nDettagli\nID campione 1;Titolo;Risultato\n{code};Uno;50.60 mg\n{code};Due;n.a.\n"
    config = AppConfig(tmp_path / "input", tmp_path / "archive", tmp_path / "errors",
                       tmp_path / "export", default_driver=instrument.name)
    config.input_dir.mkdir()
    path = config.input_dir / f"{code}.txt"
    path.write_text(text, encoding="utf-8")
    items = ImporterService(db).process_file_samples(path, config)
    assert items[0].status == "SUCCESS"
    sample = db.get_samples()[0]
    saved = db.get_sample_results(sample.id)
    assert [r.lis_substance_code for r in saved] == ["00500", "a002"]
    assert saved[0].formatted_value == "50,60" and saved[1].formatted_value == "0"
    assert db.save_transcoding("Uno", "BG00611", lis_substance_code="NEW")[0]
    assert db.get_sample_results(sample.id)[0].lis_substance_code == "00500"
    path.write_text(text, encoding="utf-8")
    ImporterService(db).process_file_samples(path, config)
    merged = db.get_sample_results(sample.id)
    assert len(merged) == 2 and merged[0].id == saved[0].id
    assert merged[0].lis_substance_code == "NEW"


def test_export_matches_all_22_example_rows(db: Database, tmp_path: Path):
    """Confronta tutte le colonne con l'esempio, conservando intestazione e separatore attuali."""
    with Path("esempi/esempio_ESPORTAZIONE_sostanze.csv").open(encoding="utf-8-sig", newline="") as stream:
        reference = list(csv.DictReader(stream))
    assert len(reference) == 22
    for row in reference:
        assert db.save_transcoding("Test" + row["SOSTANZA"], row["TIPO ESAME"],
                                   lis_substance_code=row["SOSTANZA"])[0]
    first = reference[0]
    sample = SampleRecord(None, first["CODICE CAMPIONE"], "BG", int(first["ANNO"]),
                          first["ACCETTAZIONE"], int(first["CONFERIMENTO"]), int(first["CAMPIONE"]), "synthetic.txt")
    values = [result("Test" + row["SOSTANZA"], row["SOSTANZA"], row["VALORE SOSTANZA"]) for row in reference]
    _, _, sample_id = db.save_sample_with_results(sample, values)
    sample = db.get_sample_with_results(sample_id)
    ok, _, path, count = LISExporter(db).export_samples([sample], tmp_path / "export", "all.csv")
    assert ok and count == 22
    actual = read_export(path)
    for source, exported in zip(reference, actual):
        source["UNITÀ BGSURA"] = source.pop("UNITÀ MISURA")
        assert exported == source
    data = path.read_bytes()
    assert b"\r\n" in data and b"\n" not in data.replace(b"\r\n", b"")
    assert db.get_sample_with_results(sample_id).status == "ESPORTATO"


@pytest.mark.parametrize("condition,reason", [
    ("missing", "sostanze mancanti"), ("unselected", "sostanze non selezionate"),
    ("unexpected", "sostanze fuori catalogo"), ("duplicate", "sostanze duplicate"),
    ("no_catalog", "nessun catalogo sostanze attivo"),
])
def test_skip_whole_exam_but_export_standard(db: Database, tmp_path: Path, condition: str, reason: str):
    """L'esclusione di un gruppo non impedisce gli standard né marca sostanze escluse."""
    catalog(db)
    values = [result("Standard", exam="STD"), result("Uno", "00500")]
    if condition != "missing":
        values.append(result("Due", "a002"))
    if condition in ("unexpected", "duplicate"):
        values.append(result("Extra", "EXTRA" if condition == "unexpected" else "00500"))
    sample = save_sample(db, values)
    if condition == "unselected":
        sample.results = sample.results[:2]
    if condition == "no_catalog":
        with db.get_connection() as conn:
            conn.execute("UPDATE transcodings SET is_active=0 WHERE lis_substance_code IS NOT NULL")
    ok, message, path, count = LISExporter(db).export_samples([sample], tmp_path / "export", "mixed.csv")
    assert ok and count == 1 and reason in message and sample.sample_code in message
    rows = read_export(path)
    assert rows[0]["VALORE"] == "50,60" and rows[0]["SOSTANZA"] == ""
    assert rows[0]["VALORE SOSTANZA"] == "" and rows[0]["TIPO ESAME"] == "STD"
    saved = db.get_sample_with_results(sample.id)
    assert saved.status == "DA_ESPORTARE"
    assert saved.results[0].is_exported
    assert all(not r.is_exported for r in saved.results[1:])
    with db.get_connection() as conn:
        audit = conn.execute("SELECT details FROM audit_logs WHERE action='EXPORT_LIS_SKIPPED'").fetchone()
        assert reason in audit[0]


def test_no_valid_rows_creates_no_file_and_keeps_status(db: Database, tmp_path: Path):
    """Un esame incompleto da solo non produce CSV, nemmeno una sola intestazione."""
    catalog(db)
    sample = save_sample(db, [result("Uno", "00500")])
    ok, message, path, count = LISExporter(db).export_samples([sample], tmp_path / "absent", "none.csv")
    assert not ok and count == 0 and "a002" in message
    assert not path.exists() and not path.parent.exists()
    assert db.get_sample_with_results(sample.id) == sample


def test_only_written_samples_are_counted_and_marked_without_result_ids(db: Database, tmp_path: Path):
    """Anche i risultati originari senza ID non marcano gli esami saltati."""
    catalog(db)
    values = [result("Standard", exam="STD"), result("Uno", "00500")]
    sample = save_sample(db, values)
    sample.results = values  # Contratto storico: oggetti del driver prima del ricaricamento.
    skipped = save_sample(db, [result("Uno", "00500")], "BG2600104430010001")
    ok, message, _, count = LISExporter(db).export_samples([sample, skipped], tmp_path, "counts.csv")
    assert ok and count == 1 and "Esportati 1 campioni" in message
    assert [r.is_exported for r in db.get_sample_results(sample.id)] == [True, False]
    assert not db.get_sample_results(skipped.id)[0].is_exported


def test_complete_group_and_standard_with_same_exam(db: Database, tmp_path: Path):
    """Lo snapshot senza sostanza rimane standard; zero è una misura presente valida."""
    catalog(db)
    sample = save_sample(db, [result("Standard"), result("Uno", "00500", "0"), result("Due", "a002")])
    ok, _, path, count = LISExporter(db).export_samples([sample], tmp_path, "complete.csv")
    assert ok and count == 3
    rows = read_export(path)
    assert rows[0]["VALORE"] == "50,60" and rows[0]["VALORE SOSTANZA"] == ""
    assert rows[1]["SOSTANZA"] == "00500" and rows[1]["VALORE SOSTANZA"] == "0"
    assert all(row["VALORE"] == "" for row in rows[1:])


def test_catalog_changes_do_not_rewrite_stored_codes(db: Database, tmp_path: Path):
    """Il catalogo corrente governa la completezza senza rimappare lo storico."""
    catalog(db)
    sample = save_sample(db, [result("Uno", "00500"), result("Due", "a002")])
    assert db.save_transcoding("Due", "BG00611", lis_substance_code="NEW")[0]
    ok, message, path, _ = LISExporter(db).export_samples([sample], tmp_path, "changed.csv")
    assert not ok and not path.exists() and "NEW" in message and "a002" in message
    assert db.get_sample_with_results(sample.id) == sample


def test_correction_requires_manual_complete_reexport(db: Database, tmp_path: Path):
    """Una rettifica conserva gli stati e viene reinviata solo insieme al resto dell'esame."""
    catalog(db)
    sample = save_sample(db, [result("Uno", "00500"), result("Due", "a002")])
    exporter = LISExporter(db)
    assert exporter.export_samples([sample], tmp_path, "first.csv")[0]
    before = db.get_sample_with_results(sample.id)
    assert db.save_sample_with_results(sample, [result("Uno", "00500", "51,70")], merge=True)[0]
    corrected = db.get_sample_with_results(sample.id)
    assert corrected.status == "ESPORTATO"
    assert all(r.is_exported for r in corrected.results)
    assert [r.exported_at for r in corrected.results] == [r.exported_at for r in before.results]
    corrected.results = corrected.results[:1]
    assert not exporter.export_samples([corrected], tmp_path, "partial.csv")[0]
    corrected = db.get_sample_with_results(sample.id)
    assert exporter.export_samples([corrected], tmp_path, "full.csv")[0]
    rows = read_export(tmp_path / "full.csv")
    assert len(rows) == 2 and rows[0]["VALORE SOSTANZA"] == "51,70"
    assert rows[1]["VALORE SOSTANZA"] == "50,60"


def test_overwrite_persists_substance_codes(db: Database):
    """La modalità esplicita overwrite conserva il nuovo campo nei record ricreati."""
    sample = save_sample(db, [result("Uno", "00500")])
    assert db.save_sample_with_results(sample, [result("Due", "a002")], overwrite=True)[0]
    saved = db.get_sample_results(sample.id)
    assert len(saved) == 1 and saved[0].lis_substance_code == "a002"


def verify_substance_dialogs(path: Path) -> None:
    """Esercita i dialoghi reali in un processo con un solo interprete Tk."""
    db = Database(path)
    ctk_root = ctk.CTk()
    ctk_root.withdraw()
    user = db.get_user_by_username("admin")
    SessionManager.set_user(user)
    errors = []
    messagebox.showerror = lambda *a, **k: errors.append(a)
    settings = SettingsDialog(ctk_root, db)
    try:
        settings._show_add_transcoding_dialog()
        dialog = next(w for w in settings.winfo_children() if isinstance(w, ctk.CTkToplevel))
        entries = [w for w in dialog.winfo_children() if isinstance(w, ctk.CTkEntry)]
        for entry, text in zip(entries, ["Uno", "BG00611", "00500", "Descrizione"]):
            entry.insert(0, text)
        next(w for w in dialog.winfo_children() if isinstance(w, ctk.CTkButton)).invoke()
        assert not errors
        rule = db.get_transcoding_rules_map()["Uno"]
        assert rule.lis_substance_code == "00500"
        item = next(i for i in settings.tree_trans.get_children() if settings.tree_trans.set(i, "param") == "Uno")
        settings.tree_trans.selection_set(item)
        settings._show_edit_transcoding_dialog()
        dialog = next(w for w in settings.winfo_children() if isinstance(w, ctk.CTkToplevel))
        entries = [w for w in dialog.winfo_children() if isinstance(w, ctk.CTkEntry)]
        assert entries[2].get() == "00500" and entries[3].get() == "Descrizione"
        next(w for w in dialog.winfo_children() if isinstance(w, ctk.CTkButton)).invoke()
        assert not errors and db.get_transcoding_by_id(rule.id).lis_substance_code == "00500"
        settings.destroy()
        sample = save_sample(db, [result("Uno", "00500")])
        view = MasterDetailView(ctk_root, db, user, lambda: None)
        try:
            view._display_sample_detail(sample)
            assert view.tree_detail.heading("substance", "text") == "Codice sostanza LIS"
            assert view.tree_detail.set(str(sample.results[0].id), "substance") == "00500"
        finally:
            view.destroy()
    finally:
        if settings.winfo_exists():
            settings.destroy()
        SessionManager.logout()
        ctk_root.destroy()


def test_gui_add_edit_and_detail_preserve_leading_zero_codes(tmp_path: Path):
    """Isola il test dei dialoghi per non lasciare callback Tk nella suite principale."""
    test_path = Path(__file__).resolve()
    code = "from pathlib import Path; import runpy, sys; runpy.run_path(sys.argv[1])['verify_substance_dialogs'](Path(sys.argv[2]))"
    process = subprocess.run([sys.executable, "-c", code, str(test_path), str(tmp_path / "gui.db")],
                             cwd=test_path.parents[1], capture_output=True, text=True, timeout=45)
    assert process.returncode == 0, process.stdout + process.stderr
