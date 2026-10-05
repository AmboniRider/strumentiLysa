"""Test per la Guida e il Manuale d'Uso (HelpDialog e manuale.md).

Verifica la completezza dei contenuti del manuale utente, l'inizializzazione
della finestra HelpDialog, la navigazione dell'indice (TOC), la ricerca testuale
e la visibilità del pulsante 'Guida' per tutti i ruoli (OPERATORE e ADMIN).
"""

from pathlib import Path
import customtkinter as ctk
import pytest

from src.database import Database
from src.gui.help_dialog import HelpDialog
from src.gui.master_detail import MasterDetailView
from src.models import UserRecord


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    """Fixture per istanziare un database di test isolato."""
    db_file = tmp_path / "help_test.db"
    return Database(db_file)


def test_manual_file_content_and_structure():
    """Verifica che il file manuale.md esista e contenga tutti i capitoli richiesti."""
    manual_path = Path("manuale.md")
    assert manual_path.exists(), "Il file manuale.md deve essere presente nella root del progetto"

    content = manual_path.read_text(encoding="utf-8")
    assert len(content) > 1000, "Il contenuto del manuale deve essere esaustivo e dettagliato"

    # Verifica presenza degli argomenti chiave richiesti dal cliente
    assert "Introduzione & Scopo" in content or "Scopo del Software" in content
    assert "Strumenti Supportati" in content
    assert "Dionex" in content
    assert "Mettler Toledo" in content
    assert "Selezione e Deselezione" in content
    assert "Doppio Clic" in content or "doppio clic" in content
    assert "Spazio" in content or "barra spaziatrice" in content
    assert "Duplicati" in content or "duplicati" in content
    assert "Smart Merge" in content or "Unione Intelligente" in content
    assert "Da Inviare" in content
    assert "Inviato" in content
    assert "Da Esportare" in content
    assert "Esportato" in content
    assert "24 Colonne" in content or "24 colonne" in content
    assert "Transcodifiche" in content or "transcodifiche" in content
    assert "FAQ" in content or "Domande Frequenti" in content


def test_help_dialog_initialization_and_toc(ctk_root: ctk.CTk):
    """Verifica l'inizializzazione della finestra HelpDialog e la generazione dei capitoli TOC."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        dlg = HelpDialog(ctk_root)

        # 1. Verifica componenti base
        assert hasattr(dlg, "txt_content")
        assert hasattr(dlg, "entry_search")
        assert hasattr(dlg, "frame_toc_buttons")

        # 2. Verifica lettura testo e stato disabilitato per sola lettura
        assert dlg.txt_content.cget("state") == "disabled"
        raw_text = dlg.txt_content.get("1.0", "end")
        assert "MANUALE D'USO" in raw_text or "Strumenti ➔ LIS" in raw_text

        # 3. Verifica generazione pulsanti dell'indice capitoli (TOC)
        toc_buttons = dlg.frame_toc_buttons.winfo_children()
        assert len(toc_buttons) >= 8, f"Attesi almeno 8 pulsanti capitolo nell'indice, trovati {len(toc_buttons)}"

        # 4. Verifica navigazione capitolo
        first_chapter_title = list(dlg._chapter_indices.keys())[0]
        first_index = dlg._chapter_indices[first_chapter_title]
        dlg._jump_to_chapter(first_index)

        dlg.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()


def test_help_dialog_search_functionality(ctk_root: ctk.CTk):
    """Verifica il motore di ricerca interno del visualizzatore con evidenziazione e pulizia."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        dlg = HelpDialog(ctk_root)

        # 1. Ricerca parola chiave sicuramente presente
        dlg.entry_search.delete(0, "end")
        dlg.entry_search.insert(0, "duplicati")
        dlg._on_search()

        assert len(dlg._search_matches) > 0, "Dovrebbe trovare occorrenze per 'duplicati'"
        assert "trovati" in dlg.lbl_search_status.cget("text")
        assert dlg._current_match_idx == 0

        # 2. Ricerca termine inesistente
        dlg.entry_search.delete(0, "end")
        dlg.entry_search.insert(0, "xyz_termine_inesistente_12345")
        dlg._on_search()

        assert len(dlg._search_matches) == 0
        assert dlg.lbl_search_status.cget("text") == "Nessun risultato"

        # 3. Pulizia ricerca
        dlg._on_clear_search()
        assert dlg.entry_search.get() == ""
        assert len(dlg._search_matches) == 0
        assert dlg.lbl_search_status.cget("text") == ""

        dlg.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()


def test_help_dialog_fallback_missing_file(ctk_root: ctk.CTk, tmp_path: Path):
    """Verifica che in caso di file mancante venga visualizzato un messaggio di fallback senza crash."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        fake_path = tmp_path / "manuale_non_esistente.md"
        dlg = HelpDialog(ctk_root, manual_path=fake_path)

        text = dlg.txt_content.get("1.0", "end")
        assert "non trovato" in text or "Manuale" in text

        dlg.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()


def test_help_button_accessible_for_all_roles(test_db: Database, ctk_root: ctk.CTk):
    """Verifica che il pulsante 'Guida' sia sempre visibile sia per il ruolo OPERATORE che per ADMIN."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        op_user = UserRecord(id=1, username="operatore1", password_hash="h", salt="s", role="OPERATORE")
        admin_user = UserRecord(id=2, username="admin1", password_hash="h", salt="s", role="ADMIN")

        # 1. Test per utente OPERATORE
        view_op = MasterDetailView(
            master=ctk_root,
            db=test_db,
            current_user=op_user,
            on_logout=lambda: None
        )
        header_op = view_op.winfo_children()[0]
        has_help_op = any(
            isinstance(w, ctk.CTkButton) and "Guida" in w.cget("text")
            for w in header_op.winfo_children()
        )
        assert has_help_op is True, "Il pulsante 'Guida' deve essere presente per il ruolo OPERATORE"

        for child in ctk_root.winfo_children():
            child.destroy()

        # 2. Test per utente ADMIN
        view_admin = MasterDetailView(
            master=ctk_root,
            db=test_db,
            current_user=admin_user,
            on_logout=lambda: None
        )
        header_admin = view_admin.winfo_children()[0]
        has_help_admin = any(
            isinstance(w, ctk.CTkButton) and "Guida" in w.cget("text")
            for w in header_admin.winfo_children()
        )
        assert has_help_admin is True, "Il pulsante 'Guida' deve essere presente per il ruolo ADMIN"

    finally:
        for child in ctk_root.winfo_children():
            child.destroy()
