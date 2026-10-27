"""Collaudo LCMS su report sintetici, copie dell'esempio e database temporanei."""

import csv
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from driver import (
    Agilent5977CDriver, Agilent6460LCMSDriver, DionexICDriver,
    get_available_driver_names, get_driver, get_driver_by_name,
    parse_instrument_file, parse_instrument_samples,
)
from src.config import AppConfig
from src.database import Database
from src.exporter import LISExporter
from src.importer_service import ImporterService


EXAMPLE = Path(__file__).resolve().parents[1] / "esempi" / "Agilent6460LCMS.csv"
CODE = "BG2600037720010001"
OTHER = "BG2600037730010001"
HEADER = "SampleID,CompoundID,SampleName,Compound,CalculatedConcentration,FinalConcentration\n"


def write_report(directory: Path, text: str, encoding: str = "utf-8") -> Path:
    """Prepara un file di prova senza scrivere nelle cartelle operative."""
    report = directory / "report.csv"
    report.write_text(text, encoding=encoding)
    return report


@pytest.fixture
def pipeline(tmp_path: Path) -> tuple[Database, AppConfig, ImporterService]:
    """Isola il ciclo completo di importazione ed esportazione."""
    db = Database(tmp_path / "database.db")
    config = AppConfig(
        tmp_path / "input", tmp_path / "archive", tmp_path / "errors",
        tmp_path / "export", default_driver=Agilent6460LCMSDriver.name,
    )
    config.input_dir.mkdir()
    return db, config, ImporterService(db)


def test_example_detection_and_results(tmp_path: Path):
    """Il report reale ha 19 etichette e 21 celle, ma 82 risultati acquisibili."""
    report = tmp_path / "nome_libero.csv"
    shutil.copy2(EXAMPLE, report)
    assert Agilent6460LCMSDriver.name in get_available_driver_names()
    assert isinstance(get_driver_by_name("agilent 6460 lcms"), Agilent6460LCMSDriver)
    for preferred in (None, DionexICDriver.name, Agilent5977CDriver.name):
        assert isinstance(get_driver(report, preferred), Agilent6460LCMSDriver)
    batch = Agilent6460LCMSDriver().parse_batch(report, {"Methamidophos": "TEST"})
    assert not batch.warnings
    assert [s.sample_code for s in batch.samples] == [CODE, OTHER]
    assert all(len(s.results) == 41 for s in batch.samples)
    assert all(s.instrument_name == "Agilent 6460 LCMS" for s in batch.samples)
    assert all(s.source_filename == report.name for s in batch.samples)
    results = [r for s in batch.samples for r in s.results]
    nd = [r for r in results if r.raw_value == "ND"]
    assert len(nd) == 4 and all(r.numeric_value == 0 and r.formatted_value == "0" for r in nd)
    first = batch.samples[0].results[0]
    assert first.param_name == "Methamidophos"
    assert first.formatted_value == "9,58520825918"
    assert first.is_mapped and first.lis_exam_code == "TEST"
    assert not batch.samples[0].results[1].is_mapped
    assert len(parse_instrument_samples(report)) == 2
    assert parse_instrument_file(report).sample_code == CODE


def test_preamble_quotes_grouping_first_pair_and_sixth_column(tmp_path: Path):
    """Ignore metadati irregolari, diluizione ed extra; unisce righe non adiacenti."""
    report = write_report(tmp_path,
        'metadato,"non chiuso\n\n' + HEADER +
        f'0,0, {CODE.lower()} ," 1,2-composto ",999,1.2300e-03,100,extra\n'
        f'1,0,{OTHER},Analita,888,-12.3400\n'
        f'0,1,{CODE},Nuovo composto,777,"0,2500"\n'
        f'0,0,{CODE},"1,2-composto",666,99\n', "utf-8-sig")
    batch = Agilent6460LCMSDriver().parse_batch(report)
    assert not batch.warnings
    assert [s.sample_code for s in batch.samples] == [CODE, OTHER]
    assert [r.param_name for r in batch.samples[0].results] == ["1,2-composto", "Nuovo composto"]
    assert [r.formatted_value for r in batch.samples[0].results] == ["1,2300e-03", "0,2500"]
    assert batch.samples[0].results[0].numeric_value == pytest.approx(0.00123)
    assert batch.samples[1].results[0].formatted_value == "-12,3400"


@pytest.mark.parametrize("raw", ["", "ND", "n.a.", "testo", "NaN", "Infinity", "-inf"])
def test_non_numeric_zero_is_first_usable_value(tmp_path: Path, raw: str):
    """La conversione a zero è un risultato acquisibile e non una riga scartata."""
    report = write_report(tmp_path, HEADER +
        f"0,0,{CODE},A,999,{raw}\n0,0,{CODE},A,999,55\n")
    result = Agilent6460LCMSDriver().parse_samples(report)[0].results[0]
    assert result.raw_value == raw
    assert result.numeric_value == 0 and result.formatted_value == "0"


def test_validation_and_configured_labs(pipeline):
    """Il servizio passa i prefissi reali; il driver applica tutta la validazione."""
    db, config, importer = pipeline
    custom = "ZZ" + CODE[2:]
    report = write_report(config.input_dir, HEADER + "".join(
        f"0,0,{code},A,1,2\n" for code in (
            CODE, OTHER, custom, "BG2699037720010001", "BG260003772001000X",
            "BG123", "STD 10", "bianco", "CQ",
        )
    ))
    driver = Agilent6460LCMSDriver()
    assert [s.sample_code for s in driver.parse_samples(report)] == [CODE, OTHER]
    assert driver.parse_batch(report, allowed_labs=set()).samples == []
    config.allowed_labs_str = "ZZ"
    summary = importer.import_all(config)
    assert summary.imported_count == 1 and summary.error_count == 0
    assert db.get_samples()[0].sample_code == custom


def test_partial_rows_and_recovery(pipeline):
    """Gli scarti mantengono il numero originale e non prenotano la coppia."""
    db, config, importer = pipeline
    report = write_report(config.input_dir, "metadati\n\n" + HEADER +
        f"0,0,{CODE},A,1\n0,0,{CODE}, ,1,2\n"
        f"0,0,{CODE},A,1,3.0000\n0,0,CQ\n")
    summary = importer.import_all(config)
    assert summary.imported_count == 1 and summary.error_count == 0
    assert len(summary.warnings) == 2
    assert "Riga 4" in summary.warnings[0] and "Riga 5" in summary.warnings[1]
    assert (config.archive_dir / report.name).exists()
    sample = db.get_sample_with_results(db.get_samples()[0].id)
    assert len(sample.results) == 1 and sample.results[0].formatted_value == "3,0000"


@pytest.mark.parametrize("body", [f"0,0,{CODE},A,1\n", f"0,0,{CODE}, ,1,2\n"])
def test_all_sample_rows_malformed_go_to_errors(pipeline, body: str):
    """Senza risultati utilizzabili gli scarti richiedono la correzione del file."""
    db, config, importer = pipeline
    report = write_report(config.input_dir, HEADER + body)
    summary = importer.import_all(config)
    assert summary.error_count == 1 and summary.imported_count == 0
    assert summary.warnings and not db.get_samples()
    assert (config.error_dir / report.name).exists()


@pytest.mark.parametrize("body", ["", "0,0,CQ,Analita,1,2\n0,0,STD\n\n"])
def test_controls_or_empty_table_archived(pipeline, body: str):
    """Una tabella valida senza campioni non genera errori o campioni fittizi."""
    db, config, importer = pipeline
    report = write_report(config.input_dir, HEADER + body)
    summary = importer.import_all(config)
    assert summary.imported_count == summary.error_count == summary.skipped_count == 0
    assert summary.messages and not summary.warnings and not db.get_samples()
    assert (config.archive_dir / report.name).exists()
    with pytest.raises(ValueError, match="Nessun campione valido"):
        Agilent6460LCMSDriver().parse_file(config.archive_dir / report.name)


@pytest.mark.parametrize("text", [
    "metadati senza intestazione\n",
    HEADER.replace("SampleName", "Nome"),
    HEADER.replace("FinalConcentration", "Calculated"),
    "SampleID,CompoundID,SampleName,Compound\n",
    HEADER + f'0,0,{CODE},A,1,2\n0,0,{OTHER},B,1,"non chiuso\n',
    HEADER + f'0,0,{CODE},A,1,2\n0,0,{OTHER},B,1,"2"errore\n',
])
def test_global_error_saves_nothing(pipeline, text: str):
    """Un errore anche in coda invalida tutte le righe precedenti del file."""
    db, config, importer = pipeline
    report = write_report(config.input_dir, text)
    summary = importer.import_all(config)
    assert summary.error_count == 1 and summary.imported_count == 0
    assert not db.get_samples() and (config.error_dir / report.name).exists()


@pytest.mark.parametrize("text", ["", "Sample,A Results\n", "SampleID;SampleName;Compound\n", HEADER.replace("SampleName", "Nome")])
def test_detection_rejects_unrelated_formats(tmp_path: Path, text: str):
    """Il riconoscimento non intercetta gli altri formati strumentali."""
    driver = Agilent6460LCMSDriver()
    assert not driver.can_handle(write_report(tmp_path, text))
    assert not driver.can_handle(tmp_path / "missing.csv")


def test_example_import_export_and_merge(pipeline):
    """Verifica 82 righe LIS, snapshot sostanze e merge senza riaprire gli invii."""
    db, config, importer = pipeline
    names = [r.param_name for r in Agilent6460LCMSDriver().parse_samples(EXAMPLE)[0].results]
    for index, name in enumerate(names):
        assert db.save_transcoding(
            name, "STANDARD" if index == 0 else "GRUPPO",
            lis_substance_code=None if index == 0 else f"{index:03}",
        )[0]
    source = config.input_dir / "sequenza.csv"
    shutil.copy2(EXAMPLE, source)
    summary = importer.import_all(config)
    assert summary.imported_count == 2 and summary.error_count == 0
    assert not summary.warnings and not summary.unmapped_params_global
    assert (config.archive_dir / source.name).exists()
    samples = [db.get_sample_with_results(s.id) for s in db.get_samples()]
    assert all(len(s.results) == 41 for s in samples)
    assert all(sum(r.lis_substance_code is not None for r in s.results) == 40 for s in samples)
    ok, _, exported, count = LISExporter(db).export_samples(samples, config.export_dir)
    assert ok and count == 82
    with exported.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert all(len(row) == 24 for row in rows)
    assert sum(row["TIPO ESAME"] == "STANDARD" for row in rows) == 2
    assert sum(bool(row["SOSTANZA"]) for row in rows) == 80
    first = next(row for row in rows if row["CODICE CAMPIONE"] == CODE and row["TIPO ESAME"] == "STANDARD")
    assert first["VALORE"] == "9,58520825918"

    saved = next(s for s in samples if s.sample_code == CODE)
    # L'export aggiorna il database, non le dataclass caricate prima dell'invio:
    # rileggi lo stato persistito per verificare correttamente il merge.
    original = next(r for r in db.get_sample_results(saved.id) if r.param_name == names[0])
    text = HEADER + f"0,0,{CODE},{names[0]},99,8.5000\n0,0,{CODE},{names[0]},99,77\n"
    write_report(config.input_dir, text)
    summary = importer.import_all(config, duplicate_callback=lambda code: False)
    assert summary.skipped_count == 1 and summary.merged_count == 0
    assert next(r for r in db.get_sample_results(saved.id) if r.param_name == names[0]).formatted_value == original.formatted_value
    write_report(config.input_dir, text)
    summary = importer.import_all(config, duplicate_callback=lambda code: True)
    assert summary.merged_count == 1 and summary.error_count == 0
    updated = next(r for r in db.get_sample_results(saved.id) if r.param_name == names[0])
    assert updated.formatted_value == "8,5000" and updated.is_exported
    assert updated.exported_at == original.exported_at
    assert len(db.get_sample_results(saved.id)) == 41
    with db.get_connection() as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_settings_description():
    """Le impostazioni spiegano i campi effettivamente acquisiti dal driver."""
    from src.gui.settings_dialog import SettingsDialog

    values = {}
    dialog = SimpleNamespace(lbl_driver_info=SimpleNamespace(configure=lambda **kw: values.update(kw)))
    SettingsDialog._update_driver_info_text(dialog, Agilent6460LCMSDriver.name)
    assert "FinalConcentration (6)" in values["text"] and "SampleID" in values["text"]


@pytest.mark.parametrize("substance", [None, "001"])
def test_unknown_compounds_preserved_but_not_exported(pipeline, substance: str | None):
    """Un catalogo parziale non blocca l'acquisizione né esporta i nomi ignoti."""
    db, config, importer = pipeline
    assert db.save_transcoding("Methamidophos", "TEST_LIS", lis_substance_code=substance)[0]
    shutil.copy2(EXAMPLE, config.input_dir / "partial.csv")
    summary = importer.import_all(config)
    assert summary.imported_count == 2 and summary.error_count == 0
    assert len(summary.unmapped_params_global) == 40
    samples = [db.get_sample_with_results(s.id) for s in db.get_samples()]
    assert all(len(s.results) == 41 for s in samples)
    ok, message, output, count = LISExporter(db).export_samples(samples, config.export_dir)
    assert ok and count == 2 and "senza transcodifica LIS" in message
    with output.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert all(len(row) == 24 and row["TIPO ESAME"] == "TEST_LIS" for row in rows)
    assert all(row["SOSTANZA"] == (substance or "") for row in rows)
    for sample in samples:
        saved = db.get_sample_with_results(sample.id)
        assert saved.status == "ESPORTATO"
        assert saved.pending_results_count == 0
        assert sum(r.is_exported for r in saved.results) == 1
        assert all(not r.is_exported for r in saved.results if not r.is_mapped)
    with db.get_connection() as connection:
        assert "senza transcodifica LIS" in connection.execute(
            "SELECT details FROM audit_logs WHERE action='EXPORT_LIS_SKIPPED'"
        ).fetchone()[0]


def test_only_unknown_compounds_create_no_export(pipeline):
    """Nessuna mappatura produce acquisizione regolare e nessun CSV fittizio."""
    db, config, importer = pipeline
    write_report(config.input_dir, HEADER + f"0,0,{CODE},Parametro sconosciuto,1,2\n")
    summary = importer.import_all(config)
    assert summary.imported_count == 1 and summary.error_count == 0
    assert summary.unmapped_params_global == {"Parametro sconosciuto"}
    sample = db.get_sample_with_results(db.get_samples()[0].id)
    ok, message, output, count = LISExporter(db).export_samples([sample], config.export_dir)
    assert not ok and count == 0 and "senza transcodifica LIS" in message
    # Il servizio di importazione può aver già creato la cartella export;
    # il contratto riguarda l'assenza di file, non della directory configurata.
    assert not output.exists() and not list(config.export_dir.glob("*.csv"))
    assert db.get_sample_with_results(sample.id) == sample
