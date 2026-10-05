# PROJECT CONTEXT

## Project Goal
Applicazione desktop per l'interfacciamento tra strumenti di laboratorio (es. Cromatografo Ionico Dionex / IC e futuri strumenti) e il LIS (Laboratory Information System). Il software acquisisce file di testo generati dagli strumenti, normalizza e transcodifica i parametri, li persiste su SQLite locale e consente all'operatore di selezionare ed esportare i campioni nel tracciato CSV standard richiesto dal LIS.

## Stack
- **Linguaggio**: Python 3.11+
- **Gestore Ambienti & Pacchetti**: `uv` (`uv sync`, `uv run`)
- **GUI Framework**: `CustomTkinter`
- **Database**: `SQLite 3` (locale, embedded)
- **OS Target**: Windows (con portabilità per Linux/macOS)
- **Licenza & Compatibilità**: Pienamente compatibile con GNU AGPLv3 (tutte le dipendenze esterne dirette e indirette adottano licenze permissive compatibili: MIT, BSD-3-Clause, BSD-2-Clause, Apache-2.0, HPND/MIT-CMU, PSF License; codice sorgente interno 100% originale privo di componenti proprietari terzi).

## Main Components
- [progetto.md](file:///d:/pyprg/strumenti/progetto.md): Specifiche dettagliate e complete del progetto.
- [driver.py](file:///d:/pyprg/strumenti/driver.py): Modulo isolato contenente tutti i driver di parsing e conversione specifici degli strumenti.
- [app.py](file:///d:/pyprg/strumenti/app.py): Entry point dell'applicazione desktop con banner ANSI e gestione finestra.
- [strumenti.bat](file:///d:/pyprg/strumenti/strumenti.bat): Script batch per avvio rapido su Windows con impostazione del titolo console e codifica UTF-8.
- `sync.bat`: Sincronizzazione Git bidirezionale con commit locale automatico, fetch, merge e push; `--check` verifica i prerequisiti senza modifiche o rete.
- `.gitignore` / `.gitattributes`: Esclusione di ambienti, cache e dati operativi; normalizzazione dei testi e terminatori CRLF per i batch.
- `README.md`: Installazione da GitHub, avvio e istruzioni di sincronizzazione.
- `transfer.md`: Guida al trasferimento e installazione su PC privi di ambiente Python.
- [manuale.md](file:///d:/pyprg/strumenti/manuale.md): Manuale d'uso completo per operatori e amministratori di laboratorio (workflow, selezione campioni/test, duplicati smart merge, esportazione LIS e FAQ).
- `src/`:
  - `models.py`: Dataclass condivise per campioni, risultati, utenti, transcodifiche e filtri; contratto dati fra driver, servizi, database e GUI.
  - `importer_service.py`: Scansione manuale della cartella input, parsing mono/multi-campione, validazione, merge e archiviazione dei file.
  - `database.py`: Connessione, schema DDL, repository e migrazioni SQLite.
  - `auth.py`: Gestione sicurezza, hashing password (SHA-256 + salt), sessione e ruoli (`ADMIN`, `OPERATORE`).
  - `config.py`: Gestione impostazioni applicative e percorsi cartelle.
  - `exporter.py`: Generatore file CSV standard per il LIS (24 colonne).
  - `validator.py`: Validatore del codice campione a 18 caratteri e integrità dati.
  - `gui/`: Interfaccia grafica CustomTkinter (Login, Master-Detail per campioni/parametri, Finestra Configurazione Admin, Maschera Help/Guida Utente `help_dialog.py`).
- `driver_implementati/`: Documentazione tecnico-operativa approfondita per ciascun driver implementato ([README.md](file:///d:/pyprg/strumenti/driver_implementati/README.md), [dionex_ic.md](file:///d:/pyprg/strumenti/driver_implementati/dionex_ic.md), [mettler_toledo.md](file:///d:/pyprg/strumenti/driver_implementati/mettler_toledo.md), [spettrofotometro_uv_vis.md](file:///d:/pyprg/strumenti/driver_implementati/spettrofotometro_uv_vis.md)).

## Development Conventions
- Modulo `driver.py` rigorosamente disaccoppiato dal resto del sistema con classe base `BaseInstrumentDriver`.
- Codice campione a 18 caratteri con parsing posizionale rigoroso: Lab (1-2), Anno (3-4), Vuoto (5-6), Accettazione (7-11), Conferimento (12-14), Campione (15-18).
- Valori numerici esportati con virgola decimale e valori non numerici convertiti a `0`.
- Spostamento automatico dei file analizzati in `archiviati/` ed eventuali file errati in `errori/`.
- Unione intelligente (Merge) dei campioni duplicati: aggiunta di nuovi parametri e aggiornamento di parametri esistenti senza azzeramento o perdita di test.
- Tracciamento dello stato di esportazione LIS a livello di singolo parametro (`is_exported`, `exported_at` in `sample_results`).
- Tracciamento dello stato dei campioni (`DA_ESPORTARE`, `ESPORTATO`, `ERRORE`): un campione rimane `DA_ESPORTARE` finché contiene almeno un test pendente, e passa a `ESPORTATO` solo quando tutti i suoi parametri sono stati trasmessi.
- Visualizzazione predefinita con filtro di stato 'Da Esportare' e periodo dell'ultimo mese per mostrare prioritariamente i campioni pendenti da processare, con selettori rapidi per consultare gli esportati o l'intero storico.

## Technical Constraints
- Architettura 100% locale, nessun servizio cloud o dipendenza esterna obbligatoria.
- Nessuna perdita accidentale di dati originali (i file elaborati vengono archiviati, non cancellati).

## Current Status & Active TODO
- **Status**: Implementazione completata e verificata con successo.
- **Funzionalità Implementate**:
  - Organizzazione file di esempio e test in `esempi/`.
  - Configurazione progetto `pyproject.toml` con `uv` e ambiente virtuale dedicato.
  - Modulo isolato [driver.py](file:///d:/pyprg/strumenti/driver.py) per Cromatografo Ionico Dionex / IC e predisposizione multi-strumento.
  - Validatore posizionale [src/validator.py](file:///d:/pyprg/strumenti/src/validator.py) per codici campione a 18 caratteri con codici laboratorio configurabili.
  - Database SQLite relazionale [src/database.py](file:///d:/pyprg/strumenti/src/database.py) con seed automatico, audit logs e CRUD completo.
  - Autenticazione con hashing sicuro SHA-256 + salt e gestione ruoli (`ADMIN`, `OPERATORE`) in [src/auth.py](file:///d:/pyprg/strumenti/src/auth.py).
  - Servizio di acquisizione e archiviazione sicura [src/importer_service.py](file:///d:/pyprg/strumenti/src/importer_service.py) con gestione duplicati.
  - Esportatore CSV conforme al tracciato LIS a 24 colonne in [src/exporter.py](file:///d:/pyprg/strumenti/src/exporter.py).
  - Interfaccia grafica CustomTkinter moderna con Login, Dashboard Master-Detail, filtri temporali e filtro di stato predefinito su 'Da Esportare' in [src/gui/](file:///d:/pyprg/strumenti/src/gui/).
  - Entry point [app.py](file:///d:/pyprg/strumenti/app.py) con banner ANSI e console title secondo le regole `AGENTS.md`.
  - Script batch [strumenti.bat](file:///d:/pyprg/strumenti/strumenti.bat) per lancio con doppio clic su Windows.
  - Selezione del Driver Strumento Predefinito nell'interfaccia di configurazione (riservata esclusivamente ad utenti con ruolo Admin).
  - Modifica completa delle Regole di Transcodifica LIS nel pannello Impostazioni (aggiornamento per ID con validazione univocità, pulsante dedicato 'Modifica Regola' e doppio clic su riga tabella).
  - Ordinamento naturale cliccabile su tutte le colonne delle griglie 'Transcodifiche LIS' e 'Gestione Utenti' nel pannello Impostazioni, con indicatori grafici (▲/▼) e mantenimento dell'ordinamento al refresh.
  - Connessioni SQLite a ciclo di vita deterministico tramite context manager con chiusura garantita (`Generator[Connection]`).
  - Documentazione di installazione e trasferimento su PC privi di Python in `transfer.md`.
  - Supporto trasparente per file con padding NUL (`\x00`) esportati da strumenti a buffer fisso (es. Dionex IC a 216 byte) in [driver.py](file:///d:/pyprg/strumenti/driver.py).
  - Funzione di eliminazione campioni già esportati a partire da una data specificata (`delete_exported_samples_from_date`), riservata esclusivamente agli utenti Amministratori, con anteprima interattiva (`get_exported_samples_from_date`), scorciatoie rapide per la data, cancellazione a cascata dei parametri (`sample_results`), protezione da conferme modali e tracciamento nel log di audit (`src/database.py`, `src/gui/settings_dialog.py`, `src/gui/master_detail.py`).
  - Driver per strumento **Mettler Toledo** (`MettlerToledoDriver`) in [driver.py](file:///d:/pyprg/strumenti/driver.py): parsing report `ListReport.csv`, raggruppamento multi-campione per ID a 18 caratteri, rimozione automatica delle unità di misura dal campo Risultato (es. `'293,370 uS'` -> `'293,370'`), e transcodifica LIS per parametri multipli (`Conducibilita'` e `PH`).
  - Supporto nativo all'importazione di file multi-campione in [src/importer_service.py](file:///d:/pyprg/strumenti/src/importer_service.py): elaborazione trasparente di file contenenti N campioni, validazione posizionale per singolo campione, gestione interattiva dei duplicati per singolo campione con callback, archiviazione del file al termine dell'elaborazione di tutti i campioni.
  - Selezione Selettiva dei Test/Parametri per singolo campione: colonna interattiva `Export` con `[✓]`/`[ ]` nella tabella di dettaglio, supporto a doppio clic e barra spaziatrice, pulsanti rapidi 'Seleziona Tutti' e 'Deseleziona' dedicati al campione visualizzato, sincronizzazione bidirezionale con la tabella Master (visualizzazione `X/Y` nella colonna 'N. Parametri', auto-deselezione del campione se a 0 test, auto-selezione al ripristino di test), contatore dinamico dei test nel footer ed esportazione LIS con filtraggio selettivo dei soli parametri selezionati (`src/models.py`, `src/database.py`, `src/exporter.py`, `src/gui/master_detail.py`).
  - **Unione Intelligente dei Campioni Duplicati (Merge) & Tracciamento Esportazione LIS per Parametro**:
    - Aggiornamento DDL e migrazione retrocompatibile per `sample_results` con colonne `is_exported INTEGER DEFAULT 0` e `exported_at DATETIME`.
    - Metodo di upsert intelligente in `src/database.py`: inserisce nuovi parametri senza cancellare i precedenti e aggiorna i valori preservando lo stato `is_exported` per i test già inviati (nessun re-invio automatico non autorizzato).
    - Gestione import batch fluida in `src/importer_service.py`: integrazione automatica dei campioni senza popup continui e riepilogo finale dettagliato con conteggio dei campioni arricchiti.
    - Interfaccia grafica aggiornata in `src/gui/master_detail.py`: nuova colonna "Stato LIS" (`🟢 Inviato` / `🟠 Da Inviare`) nella tabella di dettaglio parametri, pre-spunta intelligente `[✓]` attiva solo sui parametri pendenti e mantenimento del campione nello stato `DA_ESPORTARE` finché restano parametri da inviare.
    - Metodo `mark_results_as_exported` in `src/database.py` ed esportazione selettiva in `src/exporter.py` per aggiornare singolarmente i parametri inviati e promuovere il campione a `ESPORTATO` solo quando tutti i test sono completati.
  - **Documentazione Tecnico-Operativa dei Driver Implementati (`driver_implementati/`)**:
    - Creato indice generale [driver_implementati/README.md](file:///d:/pyprg/strumenti/driver_implementati/README.md) con tabella di confronto, ciclo di vita e impostazione driver preferito.
    - Creata scheda approfondita per Cromatografo Ionico Dionex [dionex_ic.md](file:///d:/pyprg/strumenti/driver_implementati/dionex_ic.md) (formato `.txt` a tabulazioni, mono-campione, gestione buffer fisso e byte nulli NUL).
    - Creata scheda approfondita per Titolatore Mettler Toledo [mettler_toledo.md](file:///d:/pyprg/strumenti/driver_implementati/mettler_toledo.md) (report multi-campione `ListReport.csv`, separatore `;`, pulizia automatica delle unità di misura nel Risultato).
    - Creata scheda approfondita per Spettrofotometro UV-Vis [spettrofotometro_uv_vis.md](file:///d:/pyprg/strumenti/driver_implementati/spettrofotometro_uv_vis.md) (formato flessibile tab/csv, estrazione ID campione da nome file, normalizzazione fotometrica).
  - **Manuale d'Uso Completo & Maschera Help Interattiva**:
    - Creato il manuale operativo [manuale.md](file:///d:/pyprg/strumenti/manuale.md) con 10 capitoli dettagliati: scopo, formati strumentali, flusso operativo, istruzioni pratiche di selezione/deselezione (doppio clic, barra spaziatrice, pulsanti batch `X/Y`), gestione duplicati e Smart Merge, legenda stati (`🟢 Inviato`, `🟠 Da Inviare`), tracciato LIS a 24 colonne e FAQ.
    - Implementata la finestra modale `HelpDialog` in `src/gui/help_dialog.py`: layout moderno a due riquadri con indice laterale cliccabile (TOC) per salto immediato di capitolo, visualizzatore formattato e motore di ricerca in tempo reale con conteggio ed evidenziazione dei risultati.
  - **Formalizzazione Licenza GNU AGPLv3**:
    - Creato il file di licenza [LICENSE](file:///d:/pyprg/strumenti/LICENSE) con il testo integrale ufficiale della *GNU Affero General Public License v3.0*.
    - Aggiornato [pyproject.toml](file:///d:/pyprg/strumenti/pyproject.toml) con metadati `license = { file = "LICENSE" }`, classifiers standard OSI per AGPLv3+ e configurazione `[dependency-groups]` per uv.
    - Aggiunti gli header standard SPDX (`# SPDX-License-Identifier: AGPL-3.0-or-later`) e copyright in testa a tutti i 18 file sorgente Python del progetto (`app.py`, `driver.py`, moduli `src/` e sotto-pacchetto `src/gui/`).
    - Aggiornate le specifiche di progetto [progetto.md](file:///d:/pyprg/strumenti/progetto.md) e il manuale d'uso [manuale.md](file:///d:/pyprg/strumenti/manuale.md) con l'esplicitazione della licenza.
  - Suite completa di 45 test unitari, di integrazione e GUI in `tests/` con esito 100% positivo.
- **Active TODO**:
  - Test sul campo con campioni reali generati dagli strumenti di laboratorio.
  - Eventuale implementazione di driver per ulteriori tipologie di strumenti analitici in `driver.py`.
  - Verificare la selezione nell'esportazione dei campioni senza dettaglio aperto: il codice può esportare tutti i risultati se non è stata inizializzata la selezione dei singoli test. Il manuale ora richiede il controllo del dettaglio di ciascun campione prima dell'esportazione.
  - Verificare l'aggiornamento del titolo/versione durante una sessione autenticata: `AppWindow.update_app_title()` reinizializza anche la vista e richiama `show_login()`. I test attuali verificano il titolo, ma non la permanenza nella dashboard durante questa operazione.
  - Allineare la guida `transfer.md`: contiene riferimenti a `transer.md` inesistente e un conteggio storico di 18 test, mentre la suite attuale comprende 45 test.

### Ricognizione del 2026-10-05
- Flusso effettivo: `strumenti.bat` / `app.py` → `Database` → `AppWindow` → login → `MasterDetailView` → `ImporterService` / `LISExporter`.
- Schema SQLite: `users`, `configurations`, `transcodings`, `samples`, `sample_results`, `audit_logs`; connessioni con foreign key abilitate, WAL e chiusura deterministica. Il database operativo si trova in `data/strumenti.db`.
- Driver registrati: Dionex IC, Mettler Toledo e UV-Vis. Il driver preferito ha priorità se compatibile; seguono riconoscimento automatico e fallback. I driver dipendono dai modelli condivisi, senza accesso diretto a database o GUI.
- Importazione avviata manualmente dalla GUI; scansione non ricorsiva di `.txt`, `.csv`, `.dat`. I duplicati vengono uniti automaticamente nel flusso ordinario. Un file multi-campione viene archiviato se almeno un campione è gestito con successo, anche in presenza di altri campioni invalidi.
- L'esportazione genera un file locale CSV UTF-8, separatore `;`, 24 colonne e terminatori CRLF. Lo stato "Inviato" indica la generazione del CSV, senza conferma di ricezione da parte del LIS. I parametri senza transcodifica vengono esportati usando il nome parametro come codice esame.
- La selezione dei test vive nella GUI; l'esportatore rispetta la lista ricevuta. La preselezione dei parametri pendenti è gestita dalla vista di dettaglio, e il reinvio manuale dei parametri già esportati è possibile.
- Versione del pacchetto in `pyproject.toml`: `0.1.0`; versione visualizzata: impostazione `app_version` persistita nel database, default `1.0`.
- Verifica eseguita con `uv --offline --no-cache run --no-sync pytest -q -p no:cacheprovider --basetemp=.pytest-analysis-check --tb=short`: **45 passed** fuori dalla sandbox. La prima esecuzione nella sandbox ha prodotto 32 test superati e 13 errori di inizializzazione Tcl/Tk.
- Al momento della ricognizione la cartella non era un repository Git. Nessuna modifica al codice applicativo effettuata durante quella attività.

### Aggiornamento manuale del 2026-10-05
- Allineato `manuale.md` al merge effettivo: anche i valori già esportati vengono aggiornati, preservando stato e timestamp dell'esportazione precedente. Aggiunto esempio di rettifica e istruzioni per il reinvio manuale.
- Corretti percorsi predefiniti, descrizione dei driver e delle tabelle GUI, selezione dei risultati, esiti dei file multi-campione e significato degli stati. Documentati nome file `ESPORTAZIONE_YYYYMMDD_HHMMSS.csv`, tutte le 24 colonne reali e trattamento dei valori non numerici.
- Verifica mirata della guida: `uv --offline --no-cache run --no-sync pytest -q -p no:cacheprovider tests/test_help.py --basetemp=.pytest-manual-check --tb=short`, fuori dalla sandbox: **5 passed**. Nessuna modifica al codice applicativo.

### Repository e sincronizzazione del 2026-10-05
- Creato il repository GitHub privato `AmboniRider/strumentiLysa`: `https://github.com/AmboniRider/strumentiLysa`, remoto `origin`, ramo locale `main`.
- Il repository include sorgenti, documentazione, test, esempi e `uv.lock`; esclude `.venv`, cache, database e cartelle operative. Git non sostituisce il backup dei dati di laboratorio.
- `sync.bat` registra tutte le modifiche locali non ignorate, integra quelle remote tramite merge e carica i commit. Si interrompe in caso di conflitti o operazioni Git incomplete e non usa push forzati. `sync.bat --check` verificato con successo.


