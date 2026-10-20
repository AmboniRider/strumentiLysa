"""Test unitari per il modulo database.py."""

from pathlib import Path
import pytest

from src.auth import verify_password
from src.database import Database
from src.models import ParsedResult, SampleFilter, SampleRecord


def test_database_init_and_seed(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = Database(db_file)

    # Verifica utente admin creato di default
    admin = db.get_user_by_username("admin")
    assert admin is not None
    assert admin.role == "ADMIN"
    assert verify_password("admin", admin.password_hash, admin.salt)

    # Verifica transcodifiche di default
    trans_map = db.get_transcoding_map()
    assert "Fluoruri" in trans_map
    assert trans_map["Fluoruri"] == "BG00594"
    assert trans_map["Cloruri"] == "BG00590"

    # Verifica driver di default configurato
    config = db.get_config()
    assert config.default_driver == "Cromatografo Ionico (Dionex / IC)"

    # Modifica driver di default
    db.save_config_value("default_driver", "Spettrofotometro (UV-Vis / Assorbanza)")
    config_updated = db.get_config()
    assert config_updated.default_driver == "Spettrofotometro (UV-Vis / Assorbanza)"



def test_missing_admin_is_created_with_existing_users(tmp_path: Path) -> None:
    """Il bootstrap deve funzionare anche quando esistono già altri account."""
    db_file = tmp_path / "existing.db"
    db = Database(db_file)
    assert db.add_user("operatore", "password-prova", "OPERATORE")[0]
    operator = db.get_user_by_username("operatore")
    # Solo il database sintetico viene predisposto senza admin.
    with db.get_connection() as conn:
        conn.execute("DELETE FROM users WHERE username = 'admin'")

    reopened = Database(db_file)
    admin = reopened.get_user_by_username("admin")
    assert admin is not None and admin.role == "ADMIN"
    assert verify_password("admin", admin.password_hash, admin.salt)
    assert reopened.get_user_by_username("operatore") == operator


@pytest.mark.parametrize("username", ["admin", "ADMIN"])
def test_existing_admin_is_preserved_on_restart(tmp_path: Path, username: str) -> None:
    """Riavviare non deve reimpostare password o ruolo di un account esistente."""
    db_file = tmp_path / "restart.db"
    db = Database(db_file)
    admin = db.get_user_by_username("admin")
    assert db.update_user_password(admin.id, "password-personalizzata")[0]
    with db.get_connection() as conn:
        conn.execute("UPDATE users SET username = ?, role = 'OPERATORE' WHERE id = ?", (username, admin.id))
    before = db.get_user_by_username("admin")

    for _ in range(2):
        reopened = Database(db_file)
        assert reopened.get_user_by_username("admin") == before
        assert verify_password("password-personalizzata", before.password_hash, before.salt)
        with reopened.get_connection() as conn:
            assert conn.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'").fetchone()[0] == 1


def test_save_and_retrieve_sample(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = Database(db_file)

    sample = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="10442",
        conferment=1,
        sample_number=1,
        source_filename="BG2600104420010001.txt",
    )
    results = [
        ParsedResult("Fluoruri", "n.a.", 0.0, "0", "BG00594", True),
        ParsedResult("Cloruri", "0,7733", 0.7733, "0,7733", "BG00590", True),
    ]

    ok, msg, sample_id = db.save_sample_with_results(sample, results)
    assert ok is True
    assert sample_id is not None

    # Retrieve
    samples = db.get_samples(SampleFilter(status_filter="DA_ESPORTARE"))
    assert len(samples) == 1
    assert samples[0].sample_code == "BG2600104420010001"
    assert samples[0].results_count == 2

    # Duplicato senza overwrite
    ok_dup, msg_dup, _ = db.save_sample_with_results(sample, results, overwrite=False)
    assert ok_dup is False
    assert "già presente" in msg_dup

    # Duplicato con overwrite
    ok_ovw, _, _ = db.save_sample_with_results(sample, results, overwrite=True)
    assert ok_ovw is True


def test_mark_samples_as_exported(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = Database(db_file)

    sample = SampleRecord(
        id=None,
        sample_code="BG2600104420010001",
        lab_code="BG",
        year=2026,
        acceptance="10442",
        conferment=1,
        sample_number=1,
        source_filename="test.txt",
    )
    _, _, sample_id = db.save_sample_with_results(sample, [])
    assert sample_id is not None

    db.mark_samples_as_exported([sample_id], "ESPORTAZIONE_TEST.csv")
    samples = db.get_samples(SampleFilter(status_filter="ESPORTATI"))
    assert len(samples) == 1
    assert samples[0].status == "ESPORTATO"
    assert samples[0].export_filename == "ESPORTAZIONE_TEST.csv"


def test_transcodings_crud(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = Database(db_file)

    # Inizialmente abbiamo le transcodifiche di seed (es. Fluoruri)
    rules = db.get_all_transcodings()
    fluoruri_rule = next(r for r in rules if r.instrument_param_name == "Fluoruri")
    assert fluoruri_rule.lis_exam_code == "BG00594"

    # 1. Modifica codice LIS e descrizione per regola esistente
    ok, msg = db.update_transcoding(fluoruri_rule.id, "Fluoruri", "BG00999", "Descrizione aggiornata")
    assert ok is True
    assert "aggiornata" in msg

    updated_map = db.get_transcoding_map()
    assert updated_map["Fluoruri"] == "BG00999"

    # 2. Modifica nome del parametro
    ok, msg = db.update_transcoding(fluoruri_rule.id, "Fluoruri_Mod", "BG00999", "Parametro rinominato")
    assert ok is True
    updated_map2 = db.get_transcoding_map()
    assert "Fluoruri" not in updated_map2
    assert updated_map2["Fluoruri_Mod"] == "BG00999"

    # 3. Errore campi vuoti
    ok_empty, _ = db.update_transcoding(fluoruri_rule.id, "", "BG00999")
    assert ok_empty is False
    ok_empty_lis, _ = db.update_transcoding(fluoruri_rule.id, "Fluoruri_Mod", "")
    assert ok_empty_lis is False

    # 4. Errore se id non esiste
    ok_nonexistent, _ = db.update_transcoding(999999, "NuovoParam", "LIS123")
    assert ok_nonexistent is False

    # 5. Errore collisione nome già usato da un'altra regola
    # Cloruri esiste già
    ok_dup, msg_dup = db.update_transcoding(fluoruri_rule.id, "Cloruri", "BG00999")
    assert ok_dup is False
    assert "Esiste già" in msg_dup

    # 6. Cancellazione
    ok_del, _ = db.delete_transcoding(fluoruri_rule.id)
    assert ok_del is True
    map_after_del = db.get_transcoding_map()
    assert "Fluoruri_Mod" not in map_after_del


def test_delete_exported_samples_functionality(tmp_path: Path):
    """Verifica l'eliminazione dei campioni esportati a partire da una data specificata.

    Controlla:
    1. Filtro data e stato 'ESPORTATO' in anteprima (get_exported_samples_from_date).
    2. Blocco permessi per utenti non admin.
    3. Eliminazione corretta da parte di un utente admin.
    4. Mantenimento dei campioni 'DA_ESPORTARE' e dei campioni esportati antecedenti.
    5. Cancellazione a cascata dei parametri in 'sample_results'.
    6. Tracciamento dell'operazione nel log di audit.
    """
    db_file = tmp_path / "test_maint.db"
    db = Database(db_file)

    admin = db.get_user_by_username("admin")
    assert admin is not None

    # Crea un utente operatore
    db.add_user("operatore1", "password123", "OPERATORE")
    operatore = db.get_user_by_username("operatore1")
    assert operatore is not None
    assert operatore.role == "OPERATORE"

    # Inserisci 4 campioni
    def make_sample(code: str, acc: str, conf: int, samp: int) -> SampleRecord:
        return SampleRecord(
            id=None,
            sample_code=code,
            lab_code="BG",
            year=2026,
            acceptance=acc,
            conferment=conf,
            sample_number=samp,
            source_filename=f"{code}.txt",
        )

    # Campione 1: Esportato il 2026-08-15 (antecedente al cutoff)
    s1 = make_sample("BG2600100010010001", "10001", 1, 1)
    _, _, id1 = db.save_sample_with_results(s1, [ParsedResult("Cloruri", "1,0", 1.0, "1,0", "BG00590", True)])
    # Campione 2: Esportato il 2026-09-02 (dopo il cutoff)
    s2 = make_sample("BG2600100020010001", "10002", 1, 1)
    _, _, id2 = db.save_sample_with_results(s2, [ParsedResult("Fluoruri", "0,5", 0.5, "0,5", "BG00594", True)])
    # Campione 3: Esportato il 2026-09-05 (dopo il cutoff)
    s3 = make_sample("BG2600100030010001", "10003", 1, 1)
    _, _, id3 = db.save_sample_with_results(s3, [
        ParsedResult("Cloruri", "2,0", 2.0, "2,0", "BG00590", True),
        ParsedResult("Nitrati", "3,0", 3.0, "3,0", "BG00595", True),
    ])
    # Campione 4: Non ancora esportato (DA_ESPORTARE), importato il 2026-09-06
    s4 = make_sample("BG2600100040010001", "10004", 1, 1)
    _, _, id4 = db.save_sample_with_results(s4, [ParsedResult("Solfati", "4,0", 4.0, "4,0", "BG00603", True)])

    # Aggiorna manualmente gli stati di esportazione e le date
    with db.get_connection() as conn:
        conn.execute("UPDATE samples SET status = 'ESPORTATO', exported_at = '2026-08-15 10:00:00', export_filename = 'AUG.csv' WHERE id = ?", (id1,))
        conn.execute("UPDATE samples SET status = 'ESPORTATO', exported_at = '2026-09-02 11:00:00', export_filename = 'SEP1.csv' WHERE id = ?", (id2,))
        conn.execute("UPDATE samples SET status = 'ESPORTATO', exported_at = '2026-09-05 14:30:00', export_filename = 'SEP2.csv' WHERE id = ?", (id3,))
        conn.commit()

    # 1. Verifica anteprima get_exported_samples_from_date con cutoff '2026-09-01'
    preview_samples = db.get_exported_samples_from_date("2026-09-01")
    preview_codes = {s.sample_code for s in preview_samples}
    assert preview_codes == {"BG2600100020010001", "BG2600100030010001"}
    assert len(preview_samples) == 2

    # Verifica formati data alternativi (es. GG/MM/AAAA)
    preview_alt = db.get_exported_samples_from_date("01/09/2026")
    assert len(preview_alt) == 2

    # 2. Verifica blocco permessi per Operatore
    ok_op, msg_op, count_op = db.delete_exported_samples_from_date("2026-09-01", operatore)
    assert ok_op is False
    assert count_op == 0
    assert "Accesso negato" in msg_op

    # Verifica che nulla sia stato eliminato
    all_samples_after_op = db.get_samples(SampleFilter(date_filter="TUTTI"))
    assert len(all_samples_after_op) == 4

    # 3. Verifica errore per data non valida
    ok_inv, msg_inv, count_inv = db.delete_exported_samples_from_date("data-sbagliata", admin)
    assert ok_inv is False
    assert count_inv == 0

    # 4. Eliminazione da parte dell'Admin a partire dal 2026-09-01
    ok_adm, msg_adm, count_adm = db.delete_exported_samples_from_date("2026-09-01", admin)
    assert ok_adm is True
    assert count_adm == 2
    assert "Eliminati con successo 2 campioni" in msg_adm

    # 5. Verifica stato database post-eliminazione
    remaining = db.get_samples(SampleFilter(date_filter="TUTTI"))
    remaining_codes = {s.sample_code for s in remaining}
    # Devono essere rimasti SOLO s1 (esportato ad agosto) e s4 (DA_ESPORTARE)
    assert remaining_codes == {"BG2600100010010001", "BG2600100040010001"}

    # Verifica cancellazione a cascata dei parametri per id2 e id3
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM sample_results WHERE sample_id IN (?, ?)", (id2, id3))
        assert cursor.fetchone()["cnt"] == 0

        # Parametri di s1 e s4 ancora presenti
        cursor.execute("SELECT COUNT(*) AS cnt FROM sample_results WHERE sample_id = ?", (id1,))
        assert cursor.fetchone()["cnt"] == 1
        cursor.execute("SELECT COUNT(*) AS cnt FROM sample_results WHERE sample_id = ?", (id4,))
        assert cursor.fetchone()["cnt"] == 1

        # 6. Verifica log di audit
        cursor.execute("SELECT * FROM audit_logs WHERE action = 'DELETE_EXPORTED_SAMPLES'")
        audit = cursor.fetchone()
        assert audit is not None
        assert audit["username"] == "admin"
        assert "2 campioni" in audit["details"]

    # Chiamata successiva sulla stessa data deve restituire 0 eliminati
    ok_repeat, msg_repeat, count_repeat = db.delete_exported_samples_from_date("2026-09-01", admin)
    assert ok_repeat is True
    assert count_repeat == 0
    assert "Nessun campione esportato trovato" in msg_repeat


