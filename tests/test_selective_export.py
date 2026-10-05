"""Test per la selezione selettiva dei test/parametri per singolo campione."""

from pathlib import Path
import customtkinter as ctk
import pytest

from src.database import Database
from src.exporter import LISExporter
from src.gui.master_detail import MasterDetailView
from src.models import ParsedResult, SampleRecord, UserRecord


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    """Fixture per istanziare un database SQLite di test isolato."""
    db_file = tmp_path / "test_selective.db"
    return Database(db_file)


@pytest.fixture
def admin_user() -> UserRecord:
    return UserRecord(
        id=1,
        username="admin",
        password_hash="hash",
        salt="salt",
        role="ADMIN",
    )



def test_parsed_result_has_id(test_db: Database):
    """Verifica che get_sample_results e get_sample_with_results assegnino l'ID del record ai ParsedResult."""
    s = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="test.txt",
    )
    res_list = [
        ParsedResult(param_name="Cloruro", raw_value="10,5", numeric_value=10.5, formatted_value="10,5", lis_exam_code="BG001", is_mapped=True),
        ParsedResult(param_name="Nitrato", raw_value="5,2", numeric_value=5.2, formatted_value="5,2", lis_exam_code="BG002", is_mapped=True),
    ]
    _, _, sample_id = test_db.save_sample_with_results(s, res_list)
    assert sample_id is not None

    results = test_db.get_sample_results(sample_id)
    assert len(results) == 2
    assert results[0].id is not None
    assert results[1].id is not None
    assert results[0].param_name == "Cloruro"

    sample_full = test_db.get_sample_with_results(sample_id)
    assert sample_full is not None
    assert len(sample_full.results) == 2
    assert sample_full.results[0].id == results[0].id


def test_exporter_selective_test_subset(test_db: Database, tmp_path: Path):
    """Verifica che l'esportazione di un sottoinsieme di test generi solo le righe selezionate e marchi il campione come ESPORTATO."""
    exporter = LISExporter(test_db)
    s = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="test.txt",
    )
    res_list = [
        ParsedResult(param_name="Cloruro", raw_value="10,5", numeric_value=10.5, formatted_value="10,5", lis_exam_code="BG001", is_mapped=True),
        ParsedResult(param_name="Nitrato", raw_value="5,2", numeric_value=5.2, formatted_value="5,2", lis_exam_code="BG002", is_mapped=True),
        ParsedResult(param_name="Solfato", raw_value="20,0", numeric_value=20.0, formatted_value="20,0", lis_exam_code="BG003", is_mapped=True),
    ]
    _, _, sample_id = test_db.save_sample_with_results(s, res_list)
    assert sample_id is not None

    sample_full = test_db.get_sample_with_results(sample_id)
    assert sample_full is not None

    # Seleziona solo 2 dei 3 test (Cloruro e Solfato)
    sample_full.results = [sample_full.results[0], sample_full.results[2]]

    out_dir = tmp_path / "export"
    ok, msg, out_file, count = exporter.export_samples([sample_full], out_dir, "SELECTIVE_TEST.csv")
    assert ok is True
    assert count == 2

    # Verifica contenuto CSV
    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3  # 1 intestazione + 2 righe analitiche
    assert "BG001" in lines[1]
    assert "BG003" in lines[2]
    assert "BG002" not in out_file.read_text(encoding="utf-8")

    # Verifica che il campione rimanga DA_ESPORTARE finché ci sono test pendenti
    reloaded = test_db.get_sample_with_results(sample_id)
    assert reloaded is not None
    assert reloaded.status == "DA_ESPORTARE"

    # Verifica stato esportazione per singolo test
    r_map = {r.param_name: r for r in reloaded.results}
    assert r_map["Cloruro"].is_exported is True
    assert r_map["Solfato"].is_exported is True
    assert r_map["Nitrato"].is_exported is False

    # Esporta il test rimanente (Nitrato)
    reloaded.results = [r_map["Nitrato"]]
    ok2, _, _, count2 = exporter.export_samples([reloaded], out_dir, "SELECTIVE_TEST_PART2.csv")
    assert ok2 is True
    assert count2 == 1

    # Ora che tutti i test sono stati esportati, il campione passa a ESPORTATO
    reloaded_final = test_db.get_sample_with_results(sample_id)
    assert reloaded_final is not None
    assert reloaded_final.status == "ESPORTATO"
    assert all(r.is_exported for r in reloaded_final.results)


def test_exporter_skip_sample_with_zero_tests(test_db: Database, tmp_path: Path):
    """Verifica che un campione con 0 test selezionati venga escluso dall'export CSV e non venga marcato ESPORTATO."""
    exporter = LISExporter(test_db)
    s1 = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="test1.txt",
    )
    s2 = SampleRecord(
        id=None,
        sample_code="BG2600104430010001",
        lab_code="BG",
        year=2026,
        acceptance="0010443",
        conferment=1,
        sample_number=1,
        source_filename="test2.txt",
    )
    r1 = [ParsedResult(param_name="Cloruro", raw_value="10", numeric_value=10.0, formatted_value="10", lis_exam_code="BG001", is_mapped=True)]
    r2 = [ParsedResult(param_name="Nitrato", raw_value="20", numeric_value=20.0, formatted_value="20", lis_exam_code="BG002", is_mapped=True)]

    _, _, id1 = test_db.save_sample_with_results(s1, r1)
    _, _, id2 = test_db.save_sample_with_results(s2, r2)

    sample1 = test_db.get_sample_with_results(id1)
    sample2 = test_db.get_sample_with_results(id2)
    assert sample1 and sample2

    # sample1 ha 1 test, sample2 ha 0 test selezionati
    sample2.results = []

    out_dir = tmp_path / "export"
    ok, msg, out_file, count = exporter.export_samples([sample1, sample2], out_dir, "SKIP_ZERO.csv")
    assert ok is True
    assert count == 1

    lines = out_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2  # header + 1 riga

    # sample1 è ESPORTATO, sample2 resta DA_ESPORTARE
    assert test_db.get_sample_with_results(id1).status == "ESPORTATO"
    assert test_db.get_sample_with_results(id2).status == "DA_ESPORTARE"


def test_gui_selective_test_interactions(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk):
    """Verifica l'interazione grafica di selezione test e la sincronizzazione con la tabella master."""
    for child in ctk_root.winfo_children():
        child.destroy()

    s = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="0010442",
        conferment=1,
        sample_number=1,
        source_filename="test.txt",
    )
    res_list = [
        ParsedResult(param_name="Cloruro", raw_value="10,5", numeric_value=10.5, formatted_value="10,5", lis_exam_code="BG001", is_mapped=True),
        ParsedResult(param_name="Nitrato", raw_value="5,2", numeric_value=5.2, formatted_value="5,2", lis_exam_code="BG002", is_mapped=True),
        ParsedResult(param_name="Solfato", raw_value="20,0", numeric_value=20.0, formatted_value="20,0", lis_exam_code="BG003", is_mapped=True),
    ]
    _, _, sample_id = test_db.save_sample_with_results(s, res_list)
    assert sample_id is not None

    try:
        view = MasterDetailView(
            master=ctk_root,
            db=test_db,
            current_user=admin_user,
            on_logout=lambda: None
        )

        # 1. Verifica default: tutti i test selezionati
        master_item = view.tree_master.item(str(sample_id))
        assert master_item["values"][0] == " [✓] "
        assert master_item["values"][7] == "3/3"
        assert sample_id in view.selected_sample_ids

        # Verifica che il pannello detail mostri le 3 righe con [✓]
        detail_children = view.tree_detail.get_children()
        assert len(detail_children) == 3
        for r_id in detail_children:
            assert view.tree_detail.item(r_id)["values"][0] == " [✓] "

        # 2. Deseleziona un test
        first_test_id = int(detail_children[0])
        view._toggle_test_selection(first_test_id)

        # Riga nel detail diventa [  ]
        assert view.tree_detail.item(str(first_test_id))["values"][0] == " [  ] "
        # Riga nel master mostra 2/3
        master_item = view.tree_master.item(str(sample_id))
        assert master_item["values"][7] == "2/3"
        assert master_item["values"][0] == " [✓] "
        assert sample_id in view.selected_sample_ids

        # 3. Deseleziona tutti i test tramite pulsante
        view._deselect_all_tests_current_sample()
        for r_id in view.tree_detail.get_children():
            assert view.tree_detail.item(r_id)["values"][0] == " [  ] "

        master_item = view.tree_master.item(str(sample_id))
        assert master_item["values"][7] == "0/3"
        # Con 0 test, il campione viene deselezionato automaticamente nel master
        assert master_item["values"][0] == " [  ] "
        assert sample_id not in view.selected_sample_ids

        # 4. Riseleziona un singolo test: il campione deve tornare selezionato nel master
        view._toggle_test_selection(first_test_id)
        master_item = view.tree_master.item(str(sample_id))
        assert master_item["values"][7] == "1/3"
        assert master_item["values"][0] == " [✓] "
        assert sample_id in view.selected_sample_ids

        # 5. Seleziona tutti i test tramite pulsante
        view._select_all_tests_current_sample()
        for r_id in view.tree_detail.get_children():
            assert view.tree_detail.item(r_id)["values"][0] == " [✓] "
        master_item = view.tree_master.item(str(sample_id))
        assert master_item["values"][7] == "3/3"
        assert master_item["values"][0] == " [✓] "

        # 6. Se il campione ha 0 test e l'utente clicca sul master per selezionarlo,
        # tutti i test vengono ripristinati a selezionati
        view._deselect_all_tests_current_sample()
        assert sample_id not in view.selected_sample_ids
        view._toggle_sample_selection(sample_id)
        assert sample_id in view.selected_sample_ids
        master_item = view.tree_master.item(str(sample_id))
        assert master_item["values"][7] == "3/3"
        assert master_item["values"][0] == " [✓] "

    finally:
        for child in ctk_root.winfo_children():
            child.destroy()
