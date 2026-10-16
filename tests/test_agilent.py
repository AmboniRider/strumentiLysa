"""Collaudo Agilent su file copiati/generati e database esclusivamente temporanei."""

import csv
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from driver import (
    Agilent5977CDriver, DionexICDriver, MettlerToledoDriver,
    SpectrophotometerDriver, get_available_driver_names, get_driver,
    get_driver_by_name, parse_instrument_file, parse_instrument_samples,
)
from src.config import AppConfig
from src.database import Database
from src.exporter import LISExporter
from src.importer_service import ImporterService
from src.models import ParsedBatch


EXAMPLE = Path(__file__).resolve().parents[1] / "esempi" / "Agilent5977C.csv"
CODE = "BG2600143100010001"
OTHER = "RL2600046910010001"


def write_report(tmp_path: Path, text: str, encoding: str = "utf-8") -> Path:
    """Scrive un report temporaneo dal nome indipendente dal produttore."""
    path = tmp_path / "report.csv"
    path.write_text(text, encoding=encoding)
    return path


@pytest.fixture
def pipeline(tmp_path: Path) -> tuple[Database, AppConfig, ImporterService]:
    """Isola database, input, archivio, errori ed export per ogni test."""
    db = Database(tmp_path / "database.db")
    config = AppConfig(
        tmp_path / "input", tmp_path / "archive", tmp_path / "errors",
        tmp_path / "export", default_driver=Agilent5977CDriver.name,
    )
    config.input_dir.mkdir()
    return db, config, ImporterService(db)


def test_example_registration_detection_and_first_occurrence(tmp_path: Path):
    """Il riferimento reale produce 36 risultati e conserva la prima misura."""
    path = tmp_path / "sequenza_qualsiasi.csv"
    shutil.copy2(EXAMPLE, path)
    assert Agilent5977CDriver.name in get_available_driver_names()
    assert isinstance(get_driver_by_name("agilent 5977c"), Agilent5977CDriver)
    assert isinstance(get_driver(path), Agilent5977CDriver)
    # Anche con il vecchio default la struttura Agilent viene riconosciuta.
    assert isinstance(get_driver(path, DionexICDriver.name), Agilent5977CDriver)
    samples = parse_instrument_samples(path, {"cloroformio": "TEST"})
    assert [s.sample_code for s in samples] == [
        "BG2600141160010001", "BG2600142140010001", CODE, OTHER,
    ]
    assert all(len(s.results) == 9 and s.instrument_name == "Agilent 5977C" for s in samples)
    values = {r.param_name: r for r in samples[2].results}
    assert "1,2-dicloroetano" in values
    assert values["cloroformio"].raw_value == "0.6568"
    assert values["cloroformio"].formatted_value == "0,6568"
    assert values["cloroformio"].numeric_value == pytest.approx(0.6568)
    assert values["cloroformio"].lis_exam_code == "TEST"
    assert values["cloroformio"].is_mapped
    assert not values["benzene"].is_mapped
    assert parse_instrument_file(path).sample_code == samples[0].sample_code


def test_variable_exams_bom_quotes_second_row_and_precision(tmp_path: Path):
    """La seconda riga è ignorata anche se non contiene le etichette dell'esempio."""
    path = write_report(tmp_path,
        ' Sample ," 1,2-dicloroetano Results ",Nuovo esame Results,benzene\n'
        'contenuto,arbitrario\n\n'
        f' {CODE.lower()} ,0.0000,-12.3400,1.2300e-03\n', "utf-8-sig")
    batch = Agilent5977CDriver().parse_batch(path)
    assert not batch.warnings
    sample = batch.samples[0]
    assert sample.sample_code == CODE
    assert [r.param_name for r in sample.results] == ["1,2-dicloroetano", "Nuovo esame", "benzene"]
    assert [r.formatted_value for r in sample.results] == ["0,0000", "-12,3400", "1,2300e-03"]
    assert sample.results[-1].numeric_value == pytest.approx(0.00123)


@pytest.mark.parametrize("raw", ["", "ND", "n.a.", "testo", "NaN", "Infinity", "-inf"])
def test_non_numeric_becomes_zero(tmp_path: Path, raw: str):
    """Un'assenza o un testo conservano il dato grezzo ma producono zero LIS."""
    path = write_report(tmp_path, f"Sample,Analita Results\nignorata\n{CODE},{raw}\n")
    result = Agilent5977CDriver().parse_samples(path)[0].results[0]
    assert result.raw_value == raw
    assert result.formatted_value == "0" and result.numeric_value == 0


def test_configurable_labs_and_full_validation(tmp_path: Path):
    """Il filtro usa anche filler e cifre del validatore, oltre a prefisso/lunghezza."""
    custom = "ZZ" + CODE[2:]
    path = write_report(tmp_path,
        "Sample,A Results\nignorata\n"
        f"{CODE},1\n{OTHER},2\n{custom},3\n"
        "BG2699143100010001,4\nBG260014310001000X,5\nBG123,6\nCQ inizio,7\nBLK,8\n")
    driver = Agilent5977CDriver()
    assert [s.sample_code for s in driver.parse_batch(path, allowed_labs={"ZZ"}).samples] == [custom]
    assert [s.sample_code for s in driver.parse_samples(path)] == [CODE, OTHER]
    assert driver.parse_batch(path, allowed_labs=set()).samples == []


def test_ragged_rows_do_not_reserve_first_occurrence(tmp_path: Path):
    """Prima occorrenza utile: una riga scartata permette il recupero successivo."""
    path = write_report(tmp_path,
        "Sample,A Results,B Results\nignorata\n"
        f"{CODE},1\n{CODE},2.0000,3\n{CODE},9,9\n{OTHER},4,5,6\n")
    batch = Agilent5977CDriver().parse_batch(path)
    assert len(batch.samples) == 1
    assert batch.samples[0].results[0].formatted_value == "2,0000"
    assert len(batch.warnings) == 2
    assert "Riga 3" in batch.warnings[0] and "Riga 6" in batch.warnings[1]
    assert not batch.archive_if_empty


@pytest.mark.parametrize("text,expected", [
    (f"Sample,A Results, a RESULTS \nignorata\n{CODE},1,2\n", "duplicati"),
    (f"Sample,A Results,A\nignorata\n{CODE},1,2\n", "duplicati"),
    (f"Sample,A Results,\nignorata\n{CODE},1,2\n", "vuoto"),
    ("Sample,A Results\n", "Seconda riga"),
    (f"Sample,A Results\nignorata\n{CODE},1\n{OTHER},\"non chiuso\n", "CSV Agilent illeggibile"),
    (f'Sample,A Results\nignorata\n{CODE},1\n{OTHER},"2"errore\n', "CSV Agilent illeggibile"),
])
def test_global_failures_before_any_save(pipeline, text: str, expected: str):
    """Anche un errore nell'ultima riga impedisce il salvataggio delle precedenti."""
    db, config, importer = pipeline
    path = write_report(config.input_dir, text)
    summary = importer.import_all(config)
    assert summary.imported_count == 0 and summary.error_count == 1
    assert expected in summary.items[0].message
    assert db.get_samples() == []
    assert (config.error_dir / path.name).exists()
    assert not (config.archive_dir / path.name).exists()


@pytest.mark.parametrize("text", ["Sample;A Results\nignore\n", "Name,A Results\nignore\n", "Sample,A,B\nignore\n", ""])
def test_reject_unrelated_formats(tmp_path: Path, text: str):
    """Non intercetta CSV generici o il formato con punto e virgola."""
    assert not Agilent5977CDriver().can_handle(write_report(tmp_path, text))


def test_missing_path_and_legacy_batch_adapter(tmp_path: Path):
    """Il contratto batch preserva rilevamento e parsing dei driver preesistenti."""
    assert not Agilent5977CDriver().can_handle(tmp_path / "missing.csv")
    for driver, path in [
        (DionexICDriver(), Path("esempi/sequenze/BG2600104420010001.txt")),
        (MettlerToledoDriver(), Path("esempi/sequenze/ListReport.csv")),
    ]:
        batch = driver.parse_batch(path, allowed_labs=set())
        assert batch == ParsedBatch(samples=driver.parse_samples(path))
        assert isinstance(get_driver(path), type(driver))
    uv = write_report(tmp_path, "# UV-Vis\nParametro;Valore\nA;1\n")
    assert isinstance(get_driver(uv), SpectrophotometerDriver)
    unknown = write_report(tmp_path, "testo sconosciuto\n")
    assert isinstance(get_driver(unknown), DionexICDriver)


def test_controls_only_archived_without_sample_counts(pipeline):
    """I file di CQ non generano campioni né errori né falsi duplicati/salti."""
    db, config, importer = pipeline
    path = write_report(config.input_dir, "Sample,A Results\nignorata\nCQ,1\nBLK\nBG123,3\n")
    summary = importer.import_all(config)
    assert summary.total_files_found == 1
    assert summary.imported_count == summary.error_count == summary.skipped_count == 0
    assert summary.duplicate_count == summary.merged_count == 0
    assert not summary.warnings and len(summary.messages) == 1
    assert "archiviato" in summary.messages[0]
    assert db.get_samples() == [] and (config.archive_dir / path.name).exists()
    with pytest.raises(ValueError, match="Nessun campione valido"):
        Agilent5977CDriver().parse_file(config.archive_dir / path.name)


def test_import_partial_and_all_ragged(pipeline):
    """Gli scarti non diventano campioni; senza righe utilizzabili il file va in errori."""
    db, config, importer = pipeline
    text = f"Sample,A Results,B Results\nignorata\n{CODE},1\n"
    write_report(config.input_dir, text + f"{OTHER},2,3\n")
    summary = importer.import_all(config)
    assert summary.imported_count == 1 and summary.error_count == 0
    assert len(summary.warnings) == 1 and len(summary.items) == 1
    assert summary.unmapped_params_global == {"A", "B"}
    assert db.get_samples()[0].sample_code == OTHER
    write_report(config.input_dir, text)
    summary = importer.import_all(config)
    assert summary.imported_count == 0 and summary.error_count == 1
    assert len(summary.warnings) == 1 and (config.error_dir / "report.csv").exists()


def test_custom_lab_reaches_driver_through_importer(pipeline):
    """La configurazione live non viene sostituita dai prefissi predefiniti."""
    db, config, importer = pipeline
    config.allowed_labs_str = "ZZ"
    code = "ZZ" + CODE[2:]
    write_report(config.input_dir, f"Sample,A Results\nignorata\n{code},1\n{CODE},2\n")
    summary = importer.import_all(config)
    assert summary.imported_count == 1 and summary.error_count == 0
    assert db.get_samples()[0].sample_code == code


def test_example_full_pipeline_with_standard_and_substances(pipeline):
    """Import, snapshot sostanze, export a 24 colonne, conferma duplicati e merge."""
    db, config, importer = pipeline
    names = [r.param_name for r in Agilent5977CDriver().parse_samples(EXAMPLE)[0].results]
    for index, name in enumerate(names):
        if name == "benzene":
            assert db.save_transcoding(name, "STANDARD")[0]
        else:
            assert db.save_transcoding(name, "GRUPPO", lis_substance_code=f"{index:03}")[0]
    source = config.input_dir / "sequence.csv"
    shutil.copy2(EXAMPLE, source)
    summary = importer.import_all(config)
    assert summary.imported_count == 4 and summary.error_count == 0
    assert not summary.warnings and not summary.unmapped_params_global
    assert not source.exists() and (config.archive_dir / source.name).exists()
    samples = [db.get_sample_with_results(s.id) for s in db.get_samples()]
    assert len(samples) == 4 and all(len(s.results) == 9 for s in samples)
    assert all(sum(r.lis_substance_code is not None for r in s.results) == 8 for s in samples)
    ok, _, exported, count = LISExporter(db).export_samples(samples, config.export_dir)
    assert ok and count == 36
    with exported.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert all(len(row) == 24 for row in rows)
    assert sum(row["TIPO ESAME"] == "STANDARD" for row in rows) == 4
    chloroform = next(row for row in rows if row["CODICE CAMPIONE"] == CODE and row["SOSTANZA"] == "001")
    assert chloroform["VALORE SOSTANZA"] == "0,6568" and chloroform["VALORE"] == ""

    # Una reimportazione rifiutata conserva i risultati; quella accettata usa
    # il merge esistente, senza riaprire automaticamente risultati già inviati.
    text = f"Sample,cloroformio Results\nignorata\n{CODE},8.5000\n{CODE},99\n"
    write_report(config.input_dir, text)
    summary = importer.import_all(config, duplicate_callback=lambda code: False)
    assert summary.skipped_count == 1 and summary.imported_count == 0
    saved = next(s for s in samples if s.sample_code == CODE)
    original = next(r for r in db.get_sample_results(saved.id) if r.param_name == "cloroformio")
    assert original.formatted_value == "0,6568"
    write_report(config.input_dir, text)
    summary = importer.import_all(config, duplicate_callback=lambda code: True)
    assert summary.merged_count == 1 and summary.error_count == 0
    updated = next(r for r in db.get_sample_results(saved.id) if r.param_name == "cloroformio")
    assert updated.formatted_value == "8,5000" and updated.is_exported
    assert updated.exported_at == original.exported_at
    assert len(db.get_sample_results(saved.id)) == 9


@pytest.mark.parametrize("kind", ["partial", "controls", "error"])
def test_gui_summary_displays_batch_outcome(pipeline, monkeypatch, kind: str):
    """Esegue l'handler reale con importer reale, sostituendo solo widget e popup."""
    from src.gui.master_detail import MasterDetailView

    db, config, importer = pipeline
    text = "Sample,A Results\nignorata\n"
    if kind == "partial":
        text += f"{CODE},1\n{OTHER},2,3\n"
    elif kind == "controls":
        text += "CQ,1\n"
    else:
        text = f"Sample,A Results,A\nignorata\n{CODE},1,2\n"
    write_report(config.input_dir, text)
    monkeypatch.setattr(db, "get_config", lambda: config)
    monkeypatch.setattr(db, "log_action", lambda *args: None)
    calls = []
    for popup in ("showinfo", "showwarning"):
        monkeypatch.setattr(f"src.gui.master_detail.messagebox.{popup}",
                            lambda title, message, parent, popup=popup: calls.append((popup, message)))
    view = SimpleNamespace(
        db=db, importer_service=importer, current_user=SimpleNamespace(id=1, username="test"),
        _load_samples=lambda: None,
    )
    MasterDetailView._handle_import_files(view)
    popup, message = calls[0]
    if kind == "partial":
        assert popup == "showwarning" and "Righe scartate" in message and "Riga 4" in message
        assert "Nuovi campioni importati: 1" in message
    elif kind == "controls":
        assert popup == "showinfo" and "archiviato" in message
        assert "Nuovi campioni importati: 0" in message
    else:
        assert popup == "showwarning" and "duplicati" in message


def test_settings_description():
    """Verifica la descrizione dedicata nel gestore reale delle impostazioni."""
    from src.gui.settings_dialog import SettingsDialog

    values = {}
    dialog = SimpleNamespace(lbl_driver_info=SimpleNamespace(configure=lambda **kwargs: values.update(kwargs)))
    SettingsDialog._update_driver_info_text(dialog, "Agilent 5977C")
    assert "seconda riga ignorata" in values["text"]
    assert "Prima occorrenza" in values["text"]
