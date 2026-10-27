"""Verifica TXT transcodifiche, descrizioni e compatibilità su database temporanei."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Crea uno schema locale senza leggere le transcodifiche operative."""
    return Database(tmp_path / "transcodings.db")


@pytest.mark.parametrize("description", [
    "Descrizione italiana con accenti: quantità e qualità",
    'Analita "A": concentrazione',
    "Prima riga\n# questa riga è descrizione, non commento\nUltima riga",
    "Prima riga\r\nSeconda riga",
    "Prima riga\rSeconda riga",
    "",
])
@pytest.mark.parametrize("substance", [None, "00500"])
def test_description_roundtrip(db: Database, tmp_path: Path, description: str, substance: str | None):
    """Il giro esportazione/importazione conserva descrizioni e zeri iniziali."""
    assert db.save_transcoding("Analita", "BG00611", description, substance)[0]
    content = db.export_transcodings_text()
    other = Database(tmp_path / "other.db")
    assert other.import_transcodings_text(content)[0]
    rule = other.get_transcoding_rules_map()["Analita"]
    assert rule.description == description and rule.lis_substance_code == substance
    assert other.export_transcodings_text() == content


@pytest.mark.parametrize("tail", ["", ":00500"])
def test_legacy_files_preserve_description(db: Database, tail: str):
    """Due/tre campi cambiano la destinazione, senza cancellare il testo esistente."""
    assert db.save_transcoding("Analita", "VECCHIO", "Descrizione da conservare")[0]
    assert db.import_transcodings_text(f"Analita:BG00611{tail}\nNuovo:STD")[0]
    rules = db.get_transcoding_rules_map()
    assert rules["Analita"].description == "Descrizione da conservare"
    assert rules["Analita"].lis_substance_code == ("00500" if tail else None)
    assert rules["Nuovo"].description == ""


def test_four_fields_update_and_explicitly_clear_description(db: Database):
    """Il terzo campo vuoto identifica uno standard; il quarto vuoto azzera il testo."""
    assert db.save_transcoding("Analita", "STD", "Originale", "00500")[0]
    assert db.import_transcodings_text("Analita:NUOVO::Descrizione nuova")[0]
    rule = db.get_transcoding_rules_map()["Analita"]
    assert rule.description == "Descrizione nuova" and rule.lis_substance_code is None
    assert "Analita:NUOVO::Descrizione nuova\n" in db.export_transcodings_text()
    assert db.import_transcodings_text("Analita:NUOVO::")[0]
    assert db.get_transcoding_rules_map()["Analita"].description == ""


def test_exported_empty_description_clears_existing_text(db: Database, tmp_path: Path):
    """Un backup con descrizione vuota ripristina il vuoto su un DB già configurato."""
    assert db.save_transcoding("Analita", "STD", "")[0]
    content = db.export_transcodings_text()
    assert "Analita:STD::\n" in content
    other = Database(tmp_path / "restore.db")
    assert other.save_transcoding("Analita", "STD", "Testo da sostituire")[0]
    assert other.import_transcodings_text(content)[0]
    assert other.get_transcoding_rules_map()["Analita"].description == ""


@pytest.mark.parametrize("invalid", [
    'Nuovo:STD::Valido\nAnalita:STD::"descrizione non chiusa',
    'Nuovo:STD::Valido\nAnalita:STD::"descrizione"errore',
    "Nuovo:STD::Valido\nAnalita:STD::troppi:campi",
    "Analita:STD::Modificata\nanalita:STD::Duplicata",
    "Analita:STD::Modificata\nA:GR:00500:Prima\nB:GR:00500:Seconda",
])
def test_description_errors_are_atomic(db: Database, invalid: str):
    """Errori di quoting e conflitti non applicano neanche descrizioni precedenti."""
    assert db.save_transcoding("Analita", "STD", "Originale")[0]
    before = db.get_all_transcodings()
    ok, message = db.import_transcodings_text(invalid)
    assert not ok and "Nessuna regola importata" in message
    assert db.get_all_transcodings() == before


def test_comments_bom_and_multiline_line_numbers(db: Database):
    """I commenti esterni non sono CSV; gli errori riportano la riga fisica corretta."""
    assert db.import_transcodings_text('\ufeff# commento:"non chiuso\n\nAnalita:STD::Valido\n')[0]
    before = db.get_all_transcodings()
    ok, message = db.import_transcodings_text('Analita:STD::"Prima\nSeconda"\nmalformata\n')
    assert not ok and "Riga 3" in message
    assert db.get_all_transcodings() == before


def test_sqlite_failure_rolls_back_descriptions(db: Database):
    """Anche un fallimento dopo la prima scrittura ripristina la descrizione."""
    assert db.save_transcoding("Analita", "STD", "Originale")[0]
    before = db.get_all_transcodings()
    with db.get_connection() as conn:
        conn.execute("""CREATE TRIGGER reject_description BEFORE INSERT ON transcodings
                        WHEN NEW.instrument_param_name='Rifiuta'
                        BEGIN SELECT RAISE(ABORT, 'errore simulato'); END""")
    assert not db.import_transcodings_text("Analita:STD::Nuova\nRifiuta:STD::Test")[0]
    assert db.get_all_transcodings() == before


def test_gui_file_handlers_preserve_description(db: Database, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Esegue i veri handler di file, sostituendo solo selettori e popup."""
    from src.gui.settings_dialog import SettingsDialog

    description = 'Quantità: analita "A"\r\n# seconda riga'
    assert db.save_transcoding("Analita", "BG00611", description, "00500")[0]
    target = tmp_path / "transcodifiche.txt"
    calls = []
    monkeypatch.setattr("src.gui.settings_dialog.filedialog.asksaveasfilename", lambda **kw: str(target))
    monkeypatch.setattr("src.gui.settings_dialog.filedialog.askopenfilename", lambda **kw: str(target))
    for popup in ("showinfo", "showerror"):
        monkeypatch.setattr(f"src.gui.settings_dialog.messagebox.{popup}",
                            lambda *args, popup=popup, **kw: calls.append(popup))
    source = SimpleNamespace(db=db)
    SettingsDialog._export_transcodings_to_file(source)
    other = Database(tmp_path / "gui_import.db")
    refreshed = []
    destination = SimpleNamespace(db=other, _refresh_transcodings_list=lambda: refreshed.append(True),
                                  on_config_changed=None)
    SettingsDialog._import_transcodings_from_file(destination)
    assert calls == ["showinfo", "showinfo"] and refreshed == [True]
    rule = other.get_transcoding_rules_map()["Analita"]
    assert rule.description == description and rule.lis_substance_code == "00500"
    with other.get_connection() as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
