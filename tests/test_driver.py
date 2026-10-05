"""Test unitari per il modulo driver.py."""

from pathlib import Path
from driver import DionexICDriver, get_driver, parse_instrument_file

SAMPLE_1_PATH = Path("esempi/sequenze/BG2600104420010001.txt")
SAMPLE_2_PATH = Path("esempi/sequenze/BG2600104430010001.txt")


def test_dionex_driver_can_handle():
    driver = DionexICDriver()
    assert driver.can_handle(SAMPLE_1_PATH) is True
    assert driver.can_handle(SAMPLE_2_PATH) is True


def test_get_driver_returns_dionex():
    driver = get_driver(SAMPLE_1_PATH)
    assert isinstance(driver, DionexICDriver)


def test_parse_sample_1_structure():
    transcode_map = {
        "Fluoruri": "BG00594",
        "Cloriti": "BG00589",
        "Cloruri": "BG00590",
        "Nitriti": "BG00596",
        "Clorati": "BG00588",
        "Nitrati": "BG00595",
        "Solfati": "BG00603",
    }
    parsed = parse_instrument_file(SAMPLE_1_PATH, transcode_map)
    assert parsed.sample_code == "BG2600104420010001"
    assert len(parsed.results) == 7

    # Verifica conversione 'n.a.' in 0 e formattazione con virgola
    results_by_name = {r.param_name: r for r in parsed.results}

    # Fluoruri era 'n.a.'
    fluoruri = results_by_name["Fluoruri"]
    assert fluoruri.raw_value == "n.a."
    assert fluoruri.numeric_value == 0.0
    assert fluoruri.formatted_value == "0"
    assert fluoruri.lis_exam_code == "BG00594"
    assert fluoruri.is_mapped is True

    # Cloruri era '0,7733'
    cloruri = results_by_name["Cloruri"]
    assert cloruri.raw_value == "0,7733"
    assert abs(cloruri.numeric_value - 0.7733) < 0.0001
    assert cloruri.formatted_value == "0,7733"
    assert cloruri.lis_exam_code == "BG00590"

    # Nitrati era '8,6948'
    nitrati = results_by_name["Nitrati"]
    assert nitrati.formatted_value == "8,6948"
    assert nitrati.lis_exam_code == "BG00595"


def test_parse_sample_2_structure():
    parsed = parse_instrument_file(SAMPLE_2_PATH)
    assert parsed.sample_code == "BG2600104430010001"
    assert len(parsed.results) == 7


def test_available_drivers_and_selection():
    from driver import get_available_driver_names, get_driver_by_name, SpectrophotometerDriver

    names = get_available_driver_names()
    assert "Cromatografo Ionico (Dionex / IC)" in names
    assert "Spettrofotometro (UV-Vis / Assorbanza)" in names

    driver_dionex = get_driver_by_name("Cromatografo Ionico (Dionex / IC)")
    assert isinstance(driver_dionex, DionexICDriver)

    driver_uv = get_driver_by_name("Spettrofotometro (UV-Vis / Assorbanza)")
    assert isinstance(driver_uv, SpectrophotometerDriver)

    # Verifica get_driver con preferred_driver_name
    drv = get_driver(SAMPLE_1_PATH, preferred_driver_name="Cromatografo Ionico (Dionex / IC)")
    assert isinstance(drv, DionexICDriver)


def test_driver_handles_null_padded_files():
    """Verifica che il driver gestisca e sanitizzi correttamente i file con byte nulli di padding."""
    seq_dir = Path("sequenze")
    file1 = seq_dir / "BG2600036500010001.txt"
    if not file1.exists():
        file1 = Path("archiviati") / "BG2600036500010001.txt"
    file2 = seq_dir / "BG2600036500020001.txt"
    if not file2.exists():
        file2 = Path("archiviati") / "BG2600036500020001.txt"
    file3 = seq_dir / "BG2600036500030001.txt"
    if not file3.exists():
        file3 = Path("archiviati") / "BG2600036500030001.txt"

    driver = DionexICDriver()
    assert driver.can_handle(file1) is True
    assert driver.can_handle(file2) is True
    assert driver.can_handle(file3) is True

    parsed1 = driver.parse_file(file1)
    assert parsed1.sample_code == "BG2600036500010001"
    assert "\x00" not in parsed1.sample_code
    assert len(parsed1.results) == 7
    for r in parsed1.results:
        assert "\x00" not in r.param_name
        assert "\x00" not in r.raw_value
        assert "\x00" not in r.formatted_value

    parsed2 = driver.parse_file(file2)
    assert parsed2.sample_code == "BG2600036500020001"
    assert "\x00" not in parsed2.sample_code
    assert len(parsed2.results) == 7

    parsed3 = driver.parse_file(file3)
    assert parsed3.sample_code == "BG2600036500030001"
    assert len(parsed3.results) == 7


def test_mettler_toledo_driver_registered_and_selection():
    """Verifica la registrazione e la selezione del driver Mettler Toledo."""
    from driver import MettlerToledoDriver, get_available_driver_names, get_driver_by_name

    names = get_available_driver_names()
    assert "Mettler Toledo" in names

    driver = get_driver_by_name("Mettler Toledo")
    assert isinstance(driver, MettlerToledoDriver)


def test_mettler_toledo_can_handle():
    """Verifica il riconoscimento corretto dei file Mettler Toledo basato su nome e contenuto."""
    from driver import MettlerToledoDriver

    driver = MettlerToledoDriver()
    mettler_file = Path("esempi/sequenze/ListReport.csv")
    dionex_file = Path("esempi/sequenze/BG2600104420010001.txt")

    assert driver.can_handle(mettler_file) is True
    assert driver.can_handle(dionex_file) is False


def test_mettler_toledo_extract_numeric_result():
    """Verifica la rimozione delle unità di misura e la normalizzazione dei valori."""
    from driver import MettlerToledoDriver

    # Valore con unità di misura 'uS'
    num_val, fmt_val = MettlerToledoDriver._extract_numeric_result("293,370 uS")
    assert abs(num_val - 293.37) < 0.001
    assert fmt_val == "293,370"

    # Valore con virgola senza unità
    num_val, fmt_val = MettlerToledoDriver._extract_numeric_result("7,348")
    assert abs(num_val - 7.348) < 0.001
    assert fmt_val == "7,348"

    # Valore con punto decimale ed eventuale unità
    num_val, fmt_val = MettlerToledoDriver._extract_numeric_result("12.45 mg/L")
    assert abs(num_val - 12.45) < 0.001
    assert fmt_val == "12,45"

    # Valore non numerico
    num_val, fmt_val = MettlerToledoDriver._extract_numeric_result("n.a.")
    assert num_val == 0.0
    assert fmt_val == "0"


def test_mettler_toledo_parse_samples_structure():
    """Verifica il parsing multi-campione completo del file ListReport.csv."""
    from driver import MettlerToledoDriver

    driver = MettlerToledoDriver()
    mettler_file = Path("esempi/sequenze/ListReport.csv")

    trans_map = {
        "Conducibilita'": "BG00591",
        "PH": "BG00598",
    }

    samples = driver.parse_samples(mettler_file, trans_map)
    assert len(samples) == 3

    codes = [s.sample_code for s in samples]
    assert codes == ["BG2600036590010001", "BG2600036590020001", "BG2600036590030001"]

    # Verifica il primo campione
    s1 = samples[0]
    assert s1.sample_code == "BG2600036590010001"
    assert s1.instrument_name == "Mettler Toledo"
    assert len(s1.results) == 2

    res_map = {r.param_name: r for r in s1.results}
    assert "Conducibilita'" in res_map
    assert "PH" in res_map

    cond = res_map["Conducibilita'"]
    assert abs(cond.numeric_value - 293.37) < 0.001
    assert cond.formatted_value == "293,370"
    assert cond.raw_value == "293,370"  # Unità rimossa fin dall'acquisizione
    assert cond.lis_exam_code == "BG00591"
    assert cond.is_mapped is True

    ph = res_map["PH"]
    assert abs(ph.numeric_value - 7.348) < 0.001
    assert ph.formatted_value == "7,348"
    assert ph.raw_value == "7,348"
    assert ph.lis_exam_code == "BG00598"
    assert ph.is_mapped is True


