"""Test di integrazione end-to-end per l'intero flusso di lavoro:

Acquisizione -> Parsing -> Validazione -> DB -> Esportazione LIS -> Spostamento File.
"""

import shutil
from pathlib import Path

from src.config import AppConfig
from src.database import Database
from src.exporter import LISExporter, LIS_CSV_HEADER
from src.importer_service import ImporterService
from src.models import SampleFilter


def test_full_pipeline_workflow(tmp_path: Path):
    # 1. Configurazione cartelle temporanee
    in_dir = tmp_path / "sequenze"
    arch_dir = tmp_path / "archiviati"
    err_dir = tmp_path / "errori"
    exp_dir = tmp_path / "export"
    db_file = tmp_path / "data" / "strumenti_test.db"

    cfg = AppConfig(
        input_dir=in_dir,
        archive_dir=arch_dir,
        error_dir=err_dir,
        export_dir=exp_dir,
    )
    cfg.ensure_directories()

    db = Database(db_file)
    importer = ImporterService(db)
    exporter = LISExporter(db)

    # 2. Copia i due file di test reali nella cartella di ingresso
    s1_src = Path("esempi/sequenze/BG2600104420010001.txt")
    s2_src = Path("esempi/sequenze/BG2600104430010001.txt")
    shutil.copy2(s1_src, in_dir / s1_src.name)
    shutil.copy2(s2_src, in_dir / s2_src.name)

    # Crea anche un file non valido (codice errato)
    err_file = in_dir / "XX9999999999999999.txt"
    err_file.write_text("Sample Name:\tXX9999999999999999\n\nComponent\tAmount\nFluoruri\t1,0\n")

    # 3. Esegui l'importazione batch
    summary = importer.import_all(cfg)
    assert summary.total_files_found == 3
    assert summary.imported_count == 2
    assert summary.error_count == 1
    assert summary.duplicate_count == 0

    # 4. Verifica lo spostamento dei file
    assert len(list(in_dir.glob("*.txt"))) == 0  # Ingressi svuotati
    archived_files = list(arch_dir.glob("*.txt"))
    assert len(archived_files) == 2
    error_files = list(err_dir.glob("*.txt"))
    assert len(error_files) == 1
    assert error_files[0].name == "XX9999999999999999.txt"

    # 5. Verifica i dati registrati su SQLite
    samples_in_db = db.get_samples(SampleFilter(status_filter="DA_ESPORTARE"))
    assert len(samples_in_db) == 2

    # Verifica i parametri del primo campione
    sample_bg42 = next(s for s in samples_in_db if s.sample_code == "BG2600104420010001")
    assert sample_bg42.results_count == 7
    assert sample_bg42.status == "DA_ESPORTARE"

    results_bg42 = db.get_sample_results(sample_bg42.id)
    assert len(results_bg42) == 7

    # 6. Esegui l'esportazione per il LIS
    samples_full = [db.get_sample_with_results(s.id) for s in samples_in_db]
    ok, msg, out_file, rows = exporter.export_samples(samples_full, exp_dir)

    assert ok is True
    assert out_file.exists()
    assert rows == 14  # 7 parametri * 2 campioni

    # 7. Verifica la struttura del CSV esportato
    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 15
    assert lines[0] == ";".join(LIS_CSV_HEADER)

    # 8. Verifica l'aggiornamento di stato a ESPORTATO nel database
    exported_samples = db.get_samples(SampleFilter(status_filter="ESPORTATI"))
    assert len(exported_samples) == 2
    for s in exported_samples:
        assert s.status == "ESPORTATO"
        assert s.export_filename == out_file.name
        assert s.exported_at is not None

    # Verifica che tra i campioni da esportare non ce ne siano più
    assert len(db.get_samples(SampleFilter(status_filter="DA_ESPORTARE"))) == 0
