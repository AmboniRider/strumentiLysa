"""Test di integrazione per lo strumento Mettler Toledo:

Verifica il flusso completo per file multi-campione:
Acquisizione ListReport.csv -> Parsing MettlerToledoDriver -> Validazione codici ->
Salvataggio SQLite -> Esportazione tracciato LIS -> Archiviazione file.
"""

import shutil
from pathlib import Path

from src.config import AppConfig
from src.database import Database
from src.exporter import LISExporter, LIS_CSV_HEADER
from src.importer_service import ImporterService
from src.models import SampleFilter


def test_mettler_toledo_full_pipeline(tmp_path: Path):
    # 1. Configurazione ambiente isolato di test
    in_dir = tmp_path / "sequenze"
    arch_dir = tmp_path / "archiviati"
    err_dir = tmp_path / "errori"
    exp_dir = tmp_path / "export"
    db_file = tmp_path / "data" / "strumenti_mettler_test.db"

    cfg = AppConfig(
        input_dir=in_dir,
        archive_dir=arch_dir,
        error_dir=err_dir,
        export_dir=exp_dir,
    )
    cfg.ensure_directories()

    db = Database(db_file)
    # Assicura le transcodifiche di test per Conducibilità e PH
    with db.get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO transcodings (instrument_param_name, lis_exam_code, description) VALUES (?, ?, ?)",
            ("Conducibilita'", "BG00591", "Test Conducibilità")
        )
        conn.execute(
            "INSERT OR REPLACE INTO transcodings (instrument_param_name, lis_exam_code, description) VALUES (?, ?, ?)",
            ("PH", "BG00598", "Test PH")
        )
        conn.commit()

    importer = ImporterService(db)
    exporter = LISExporter(db)

    # 2. Copia ListReport.csv nella cartella di ingresso
    sample_src = Path("esempi/sequenze/ListReport.csv")
    shutil.copy2(sample_src, in_dir / sample_src.name)

    # 3. Esegui importazione batch
    summary = importer.import_all(cfg)

    # Verifica riepilogo batch: 1 file trovato, 3 campioni importati
    assert summary.total_files_found == 1
    assert summary.imported_count == 3
    assert summary.error_count == 0
    assert summary.duplicate_count == 0

    # 4. Verifica archiviazione file
    assert len(list(in_dir.glob("*.*"))) == 0
    assert len(list(arch_dir.glob("ListReport*.csv"))) == 1

    # 5. Verifica record salvati su SQLite
    samples_in_db = db.get_samples(SampleFilter(status_filter="DA_ESPORTARE"))
    assert len(samples_in_db) == 3

    # Mappa campioni per codice
    samples_map = {s.sample_code: s for s in samples_in_db}
    assert "BG2600036590010001" in samples_map
    assert "BG2600036590020001" in samples_map
    assert "BG2600036590030001" in samples_map

    # Verifica parametri per ciascun campione
    for code, sample in samples_map.items():
        assert sample.lab_code == "BG"
        assert sample.year == 2026
        assert sample.acceptance == "03659"
        assert sample.results_count == 2

        results = db.get_sample_results(sample.id)
        assert len(results) == 2
        r_map = {r.param_name: r for r in results}
        assert "Conducibilita'" in r_map
        assert "PH" in r_map
        assert r_map["Conducibilita'"].lis_exam_code == "BG00591"
        assert r_map["PH"].lis_exam_code == "BG00598"
        # Verifica che l'unità di misura non sia presente
        assert "uS" not in r_map["Conducibilita'"].formatted_value
        assert "uS" not in r_map["Conducibilita'"].raw_value

    # 6. Esegui esportazione CSV per LIS
    samples_full = [db.get_sample_with_results(s.id) for s in samples_in_db]
    ok, msg, out_file, rows = exporter.export_samples(samples_full, exp_dir)

    assert ok is True
    assert out_file.exists()
    assert rows == 6  # 3 campioni * 2 parametri ciascuno

    # Verifica righe CSV LIS (24 colonne con separatore ';')
    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 7  # 1 riga header + 6 righe dati
    assert lines[0] == ";".join(LIS_CSV_HEADER)

    # Verifica contenuto di una riga analitica
    data_rows = [line.split(";") for line in lines[1:]]
    for row in data_rows:
        assert len(row) == 24
        assert row[0] == "2026"     # ANNO
        assert row[1] == "03659"    # ACCETTAZIONE
        # Colonna VALORE (indice 8): deve avere virgola decimale e nessuna unità di misura
        val_str = row[8]
        assert "uS" not in val_str
        assert "," in val_str or val_str == "0"
        # Colonna TIPO ESAME (indice 10): deve essere BG00591 o BG00598
        assert row[10] in ("BG00591", "BG00598")

    # 7. Verifica gestione campioni duplicati nel file multi-campione
    # Ricopia il file nella cartella in_dir
    shutil.copy2(sample_src, in_dir / sample_src.name)

    # Importa senza autorizzare la sovrascrittura (tutti saltati)
    summary2 = importer.import_all(cfg, duplicate_callback=lambda code: False)
    assert summary2.imported_count == 0
    assert summary2.skipped_count == 3
    assert len(list(in_dir.glob("*.*"))) == 0
