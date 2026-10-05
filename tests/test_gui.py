"""Test per la GUI (MasterDetailView).

Verifica l'inizializzazione corretta dei componenti della vista principale,
in particolare il filtro di stato predefinito impostato su 'Da Esportare'.
"""

from pathlib import Path
import customtkinter as ctk
import pytest

from src.auth import SessionManager
from src.database import Database
from src.gui.master_detail import MasterDetailView
from src.gui.settings_dialog import SettingsDialog
from src.models import SampleRecord, UserRecord


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    """Fixture per istanziare un database di test isolato."""
    db_file = tmp_path / "gui_test.db"
    return Database(db_file)


@pytest.fixture
def admin_user() -> UserRecord:
    """Fixture per utente admin fittizio."""
    return UserRecord(
        id=1,
        username="admin",
        password_hash="hash",
        salt="salt",
        role="ADMIN",
    )



def test_master_detail_default_status_filter(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk):
    """Verifica che la maschera principale imposti come default lo stato 'Da Esportare'."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        view = MasterDetailView(
            master=ctk_root,
            db=test_db,
            current_user=admin_user,
            on_logout=lambda: None
        )

        # 1. Verifica valore visualizzato nella combobox
        assert view.combo_status.get() == "Da Esportare"

        # 2. Verifica che i valori disponibili contengano le opzioni corrette
        assert "Da Esportare" in view.combo_status._values
        assert "Esportati" in view.combo_status._values
        assert "Tutti" in view.combo_status._values

        # 3. Verifica che il filtro generato rifletta lo stato predefinito 'DA_ESPORTARE'
        current_filter = view._get_current_filter()
        assert current_filter.status_filter == "DA_ESPORTARE"

        # 4. Verifica modifica interattiva del filtro
        view.combo_status.set("Esportati")
        assert view._get_current_filter().status_filter == "ESPORTATI"

        view.combo_status.set("Tutti")
        assert view._get_current_filter().status_filter == "TUTTI"

        view.combo_status.set("Da Esportare")
        assert view._get_current_filter().status_filter == "DA_ESPORTARE"
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()


def test_settings_dialog_grid_sorting(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk):
    """Verifica la funzionalità di ordinamento delle griglie Transcodifica LIS e Gestione Utenti."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        SessionManager.set_user(admin_user)

        # Aggiungi alcuni utenti per testare l'ordinamento
        test_db.add_user("mario", "pwd1", "OPERATORE")
        test_db.add_user("bianchi", "pwd2", "OPERATORE")

        dlg = SettingsDialog(ctk_root, test_db)

        # =====================================================================
        # 1. Test Ordinamento Griglia Transcodifiche LIS
        # =====================================================================
        assert "param" in dlg.trans_col_titles
        assert "id" in dlg.trans_col_titles

        # Click 1: ordinamento ascendente per 'param'
        dlg._on_sort_column(dlg.tree_trans, "param", dlg.trans_col_titles, dlg._trans_sort)
        assert dlg._trans_sort["col"] == "param"
        assert dlg._trans_sort["reverse"] is False
        params_asc = [dlg.tree_trans.set(i, "param") for i in dlg.tree_trans.get_children("")]
        assert params_asc == sorted(params_asc, key=lambda s: s.lower())
        assert "▲" in dlg.tree_trans.heading("param", "text")

        # Click 2: ordinamento discendente per 'param'
        dlg._on_sort_column(dlg.tree_trans, "param", dlg.trans_col_titles, dlg._trans_sort)
        assert dlg._trans_sort["col"] == "param"
        assert dlg._trans_sort["reverse"] is True
        params_desc = [dlg.tree_trans.set(i, "param") for i in dlg.tree_trans.get_children("")]
        assert params_desc == sorted(params_asc, key=lambda s: s.lower(), reverse=True)
        assert "▼" in dlg.tree_trans.heading("param", "text")

        # Click 3: cambio colonna su 'id' (ascendente numerico)
        dlg._on_sort_column(dlg.tree_trans, "id", dlg.trans_col_titles, dlg._trans_sort)
        assert dlg._trans_sort["col"] == "id"
        assert dlg._trans_sort["reverse"] is False
        ids_asc = [int(dlg.tree_trans.set(i, "id")) for i in dlg.tree_trans.get_children("")]
        assert ids_asc == sorted(ids_asc)
        assert "▲" in dlg.tree_trans.heading("id", "text")
        # Verifica reset intestazione colonna precedente
        assert "▲" not in dlg.tree_trans.heading("param", "text")
        assert "▼" not in dlg.tree_trans.heading("param", "text")

        # Verifica preservazione ordinamento al refresh
        dlg._refresh_transcodings_list()
        ids_after_refresh = [int(dlg.tree_trans.set(i, "id")) for i in dlg.tree_trans.get_children("")]
        assert ids_after_refresh == sorted(ids_asc)

        # =====================================================================
        # 2. Test Ordinamento Griglia Gestione Utenti
        # =====================================================================
        assert "username" in dlg.users_col_titles
        assert "id" in dlg.users_col_titles

        # Click 1: ordinamento ascendente per 'username'
        dlg._on_sort_column(dlg.tree_users, "username", dlg.users_col_titles, dlg._users_sort)
        assert dlg._users_sort["col"] == "username"
        assert dlg._users_sort["reverse"] is False
        unames_asc = [dlg.tree_users.set(i, "username") for i in dlg.tree_users.get_children("")]
        assert unames_asc == sorted(unames_asc, key=lambda s: s.lower())
        assert "▲" in dlg.tree_users.heading("username", "text")

        # Click 2: ordinamento discendente per 'username'
        dlg._on_sort_column(dlg.tree_users, "username", dlg.users_col_titles, dlg._users_sort)
        assert dlg._users_sort["col"] == "username"
        assert dlg._users_sort["reverse"] is True
        unames_desc = [dlg.tree_users.set(i, "username") for i in dlg.tree_users.get_children("")]
        assert unames_desc == sorted(unames_asc, key=lambda s: s.lower(), reverse=True)
        assert "▼" in dlg.tree_users.heading("username", "text")

        # Click 3: cambio colonna su 'id' (ascendente numerico)
        dlg._on_sort_column(dlg.tree_users, "id", dlg.users_col_titles, dlg._users_sort)
        assert dlg._users_sort["col"] == "id"
        assert dlg._users_sort["reverse"] is False
        u_ids_asc = [int(dlg.tree_users.set(i, "id")) for i in dlg.tree_users.get_children("")]
        assert u_ids_asc == sorted(u_ids_asc)
        assert "▲" in dlg.tree_users.heading("id", "text")

        # Verifica preservazione ordinamento al refresh
        dlg._refresh_users_list()
        u_ids_after_refresh = [int(dlg.tree_users.set(i, "id")) for i in dlg.tree_users.get_children("")]
        assert u_ids_after_refresh == sorted(u_ids_asc)

        dlg.destroy()
    finally:
        for child in ctk_root.winfo_children():
            child.destroy()
        SessionManager.logout()


def test_settings_dialog_maintenance_tab_and_admin_button(test_db: Database, admin_user: UserRecord, ctk_root: ctk.CTk):
    """Verifica la scheda 'Manutenzione Dati' in SettingsDialog e il pulsante per gli admin."""
    for child in ctk_root.winfo_children():
        child.destroy()
    try:
        SessionManager.set_user(admin_user)

        # 1. Verifica che SettingsDialog contenga il tab Manutenzione Dati e default_tab
        dlg = SettingsDialog(ctk_root, test_db, default_tab="🧹 Manutenzione Dati")
        assert "🧹 Manutenzione Dati" in dlg.tabview._tab_dict
        assert dlg.tabview.get() == "🧹 Manutenzione Dati"
        assert hasattr(dlg, "entry_maint_date")
        assert hasattr(dlg, "tree_maint")
        assert hasattr(dlg, "btn_execute_delete")

        # Inserisci un campione esportato
        sample = SampleRecord(
            id=None,
            sample_code="BG2600109990010001",
            lab_code="BG",
            year=2026,
            acceptance="10999",
            conferment=1,
            sample_number=1,
            source_filename="test.txt",
        )
        _, _, s_id = test_db.save_sample_with_results(sample, [])
        with test_db.get_connection() as conn:
            conn.execute("UPDATE samples SET status = 'ESPORTATO', exported_at = '2026-09-08 12:00:00' WHERE id = ?", (s_id,))
            conn.commit()

        # Imposta data e aggiorna anteprima
        dlg.entry_maint_date.delete(0, "end")
        dlg.entry_maint_date.insert(0, "2026-09-01")
        dlg._refresh_maint_preview()

        items = dlg.tree_maint.get_children("")
        assert len(items) == 1
        assert "1" in dlg.lbl_maint_count.cget("text")

        dlg.destroy()

        # 2. Verifica visibilità del pulsante rapido Elimina Esportati in MasterDetailView per Admin
        view_admin = MasterDetailView(
            master=ctk_root,
            db=test_db,
            current_user=admin_user,
            on_logout=lambda: None
        )
        # Cerca un pulsante con testo "🧹 Elimina Esportati"
        has_maint_btn = any(
            isinstance(w, ctk.CTkButton) and "Elimina Esportati" in w.cget("text")
            for w in view_admin.winfo_children()[0].winfo_children()
        )
        assert has_maint_btn is True

        # 3. Verifica che per un Operatore il pulsante NON sia visibile
        op_user = UserRecord(id=2, username="operatore", password_hash="h", salt="s", role="OPERATORE")
        view_op = MasterDetailView(
            master=ctk_root,
            db=test_db,
            current_user=op_user,
            on_logout=lambda: None
        )
        has_maint_btn_op = any(
            isinstance(w, ctk.CTkButton) and "Elimina Esportati" in w.cget("text")
            for w in view_op.winfo_children()[0].winfo_children()
        )
        assert has_maint_btn_op is False

    finally:
        for child in ctk_root.winfo_children():
            child.destroy()
        SessionManager.logout()


