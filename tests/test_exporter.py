"""Test unitari per il modulo exporter.py."""

from pathlib import Path
from driver import parse_instrument_file
from src.database import Database
from src.exporter import LISExporter, LIS_CSV_HEADER
from src.models import SampleRecord
from src.validator import validate_sample_code


def test_exporter_generates_csv(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    exporter = LISExporter(db)

    # Prepara campioni di test
    trans_map = db.get_transcoding_map()
    f1 = Path("esempi/sequenze/BG2600104420010001.txt")
    f2 = Path("esempi/sequenze/BG2600104430010001.txt")

    p1 = parse_instrument_file(f1, trans_map)
    _, v1, _ = validate_sample_code(p1.sample_code)
    assert v1 is not None
    s1 = SampleRecord(
        id=None,
        sample_code=v1.raw_code,
        lab_code=v1.lab_code,
        year=v1.year_4digit,
        acceptance=v1.acceptance,
        conferment=v1.conferment,
        sample_number=v1.sample_number,
        source_filename=f1.name,
    )
    _, _, id1 = db.save_sample_with_results(s1, p1.results)
    s1.id = id1
    s1.results = p1.results

    p2 = parse_instrument_file(f2, trans_map)
    _, v2, _ = validate_sample_code(p2.sample_code)
    assert v2 is not None
    s2 = SampleRecord(
        id=None,
        sample_code=v2.raw_code,
        lab_code=v2.lab_code,
        year=v2.year_4digit,
        acceptance=v2.acceptance,
        conferment=v2.conferment,
        sample_number=v2.sample_number,
        source_filename=f2.name,
    )
    _, _, id2 = db.save_sample_with_results(s2, p2.results)
    s2.id = id2
    s2.results = p2.results

    out_dir = tmp_path / "export"
    ok, msg, out_file, count = exporter.export_samples([s1, s2], out_dir, "TEST_EXPORT.csv")
    assert ok is True
    assert out_file.exists()
    assert count == 14  # 7 parametri per 2 campioni

    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 15  # 1 intestazione + 14 righe

    # Verifica intestazione
    assert lines[0] == ";".join(LIS_CSV_HEADER)

    # Verifica prima riga dati (Fluoruri: 0, BG00594)
    cols_row1 = lines[1].split(";")
    assert len(cols_row1) == 24
    assert cols_row1[0] == "2026"
    assert cols_row1[1] == "10442"
    assert cols_row1[2] == "1"
    assert cols_row1[3] == "1"
    assert cols_row1[8] == "0"
    assert cols_row1[10] == "BG00594"
    assert cols_row1[23] == "BG2600104420010001"

    # Verifica riga con Cloruri (0,7733, BG00590)
    cols_row3 = lines[3].split(";")
    assert cols_row3[8] == "0,7733"
    assert cols_row3[10] == "BG00590"
