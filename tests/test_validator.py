"""Test unitari per il modulo validator.py."""

from src.validator import validate_sample_code


def test_valid_sample_code():
    code = "BG2600104420010001"
    is_valid, data, msg = validate_sample_code(code)
    assert is_valid is True
    assert msg == ""
    assert data is not None
    assert data.lab_code == "BG"
    assert data.year_2digit == 26
    assert data.year_4digit == 2026
    assert data.acceptance == "10442"
    assert data.conferment == 1
    assert data.conferment_str == "1"
    assert data.sample_number == 1
    assert data.sample_number_str == "1"


def test_invalid_length():
    is_valid, _, msg = validate_sample_code("BG260010442001000")  # 17 car
    assert is_valid is False
    assert "Lunghezza" in msg


def test_invalid_lab():
    is_valid, _, msg = validate_sample_code("XX2600104420010001")
    assert is_valid is False
    assert "laboratorio" in msg


def test_invalid_filler():
    is_valid, _, msg = validate_sample_code("BG2699104420010001")  # '99' invece di '00'
    assert is_valid is False
    assert "5-6" in msg


def test_non_digits():
    is_valid, _, msg = validate_sample_code("BG260010442A010001")
    assert is_valid is False
    assert "numeriche" in msg
