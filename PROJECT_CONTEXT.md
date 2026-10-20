# PROJECT CONTEXT

## Authentication Architecture — verifica del 2026-10-05
- Login desktop locale: `LoginView` cerca l'utente su SQLite, verifica la password e passa il `UserRecord` alla dashboard; nessun endpoint HTTP o provider OAuth nel codice applicativo esaminato.
- `src/auth.py` genera salt casuali di 16 byte e calcola SHA-256 di `salt:password`, verificato tramite `secrets.compare_digest`. Hash e salt sono memorizzati in `users` nel database locale `data/strumenti.db`.
- `SessionManager` conserva il record utente solo in memoria; logout azzera il riferimento. Non sono implementati token di accesso/refresh, cookie, scadenza della sessione o revoca automatica al reset password/cambio ruolo.
- Permessi `ADMIN`/`OPERATORE`: pulsanti e dialogo impostazioni protetti nella GUI; eliminazione campioni esportati protetta anche nel database. I metodi CRUD utenti non verificano autonomamente il ruolo del chiamante.
- Autenticazione GitHub separata: `sync.bat` delega a Git e al metodo di autenticazione configurato sulla postazione; non gestisce token applicativi o segreti propri. Database e file di credenziali comuni sono esclusi da Git.
- **TODO da valutare**: sostituire SHA-256 singolo con una funzione dedicata alle password; uniformare validazione password e gestione spazi; centralizzare i permessi e l'aggiornamento/revoca delle sessioni; impedire anche la declassazione dell'ultimo amministratore.
- Bootstrap concordato: a ogni inizializzazione, se manca il nome utente `admin`
  (confronto NOCASE), crearlo con password `admin` e ruolo `ADMIN`, anche con
  altri account presenti. Non reimpostare password o ruolo di account esistenti.

## Project Goal
Applicazione desktop per l'interfacciamento tra strumenti di laboratorio (es. Cromatografo Ionico Dionex / IC e futuri strumenti) e il LIS (Laboratory Information System). Il software acquisisce file di testo generati dagli strumenti, normalizza e transcodifica i parametri, li persiste su SQLite locale e consente all'operatore di selezionare ed esportare i campioni nel tracciato CSV standard richiesto dal LIS.

## Stack
- **Linguaggio**: Python 3.11+
- **Gestore Ambienti & Pacchetti**: `uv` (`uv sync`, `uv run`)
- **GUI Framework**: `CustomTkinter`
- **GUI trasferimento**: `Tkinter/ttk`, libreria standard, con worker e coda eventi.
- **Database**: `SQLite 3` (locale, embedded)
- **OS Target**: Windows (con portabilità per Linux/macOS)
- **Licenza & Compatibilità**: Pienamente compatibile con GNU AGPLv3 (tutte le dipendenze esterne dirette e indirette adottano licenze permissive compatibili: MIT, BSD-3-Clause, BSD-2-Clause, Apache-2.0, HPND/MIT-CMU, PSF License; codice sorgente interno 100% originale privo di componenti proprietari terzi).

## Main Components
- `LEGAL.md` / `src/gui/license_dialog.py`: disclaimer completo, attribuzione
  all'autore Amboni Paolo A., repository pubblico e testo integrale `LICENSE`.
  Menu principale accessibile anche prima del login e a entrambi i ruoli;
  consultazione offline in sola lettura. I documenti sono inclusi nei pacchetti.
- `src/update_service.py`: controllo Release pubbliche, confronto versioni,
  contratto manifest, whitelist runtime, checksum e download isolato.
- `src/backup.py`: copia SQLite completa, inclusi dati WAL committati, nome
  univoco e verifiche d'integrità/chiavi esterne, senza modifica del sorgente.
- `src/gui/update_dialog.py`: polling Tk e worker di rete/backup; popup a tutti,
  azioni di installazione e backup riservate ad ADMIN nelle Impostazioni.
- `update_runner.py`: bootstrap standard-library con lock di istanza, journal
  prima delle scritture, installazione esterna, rollback di file/ambiente/database
  e recupero all'avvio prima degli import applicativi.
- `maintenance.py`: migrazione su copia, nuovo database con recupero completo
  della configurazione e collaudo nascosto del vero avvio GUI.
- `build_release.py` / `.github/workflows/release.yml`: ZIP aggiornamento senza
  database e manifest formato 1; verifica su Windows e pubblicazione di Release
  da tag stabile. Il workflow su `main` può essere avviato anche per un tag
  esistente. `UPDATES.md` descrive adozione, backup e pubblicazione.
- `driver.py`: include `Agilent5977CDriver`, CSV tabulare multi-campione riconosciuto
  dal contenuto; prima riga utile per codice e controlli esclusi tramite validatore.
- `ParsedBatch` in `src/models.py`: campioni, avvisi di riga e archiviazione vuota;
  `parse_batch` adatta gli altri driver e riceve i laboratori configurati.
- `strumenti.ico`: icona della finestra principale e dei dialoghi, caricata da
  `src/gui/app_window.py` tramite percorso assoluto e inclusa nel trasferimento.
- `trasfer.py` / `transfer.bat`: creazione ZIP Windows x64 tramite elenco esplicito;
  backup SQLite ripulito da campioni, risultati e audit; installer e launcher
  distribuiti generati con uv 0.12.14, Python 3.12.13 e dipendenze runtime bloccate.
- [progetto.md](file:///d:/pyprg/strumenti/progetto.md): Specifiche dettagliate e complete del progetto.
- [driver.py](file:///d:/pyprg/strumenti/driver.py): Modulo isolato contenente tutti i driver di parsing e conversione specifici degli strumenti.
- [app.py](file:///d:/pyprg/strumenti/app.py): Entry point dell'applicazione desktop con banner ANSI e gestione finestra.
- [strumenti.bat](file:///d:/pyprg/strumenti/strumenti.bat): Script batch per avvio rapido su Windows con impostazione del titolo console e codifica UTF-8.
- `sync.bat`: Sincronizzazione Git bidirezionale con commit locale automatico, fetch, merge e push; `--check` verifica i prerequisiti senza modifiche o rete.
- `.gitignore` / `.gitattributes`: Esclusione di ambienti, cache e dati operativi; normalizzazione dei testi e terminatori CRLF per i batch.
- `README.md`: Installazione da GitHub, avvio e istruzioni di sincronizzazione.
- [transfer.md](file:///d:/pyprg/strumenti/transfer.md): Guida al trasferimento e installazione su PC privi di ambiente Python (dettaglio file da copiare e da escludere).
- [manuale.md](file:///d:/pyprg/strumenti/manuale.md): Manuale d'uso completo per operatori e amministratori di laboratorio (workflow, selezione campioni/test, duplicati smart merge, esportazione LIS e FAQ).
- `src/`:
  - `models.py`: Dataclass condivise per campioni, risultati, utenti, transcodifiche e filtri; contratto dati fra driver, servizi, database e GUI.
  - `importer_service.py`: Scansione manuale della cartella input, parsing mono/multi-campione, validazione, merge e archiviazione dei file.
  - `database.py`: Connessione, schema DDL, repository e migrazioni SQLite.
    Eliminazione utenti con scollegamento dei soli `audit_logs.user_id`, storico
    preservato e gestione transazionale degli errori SQLite per la GUI.
  - `auth.py`: Gestione sicurezza, hashing password (SHA-256 + salt), sessione e ruoli (`ADMIN`, `OPERATORE`).
  - `config.py`: Gestione impostazioni applicative e percorsi cartelle.
  - `exporter.py`: Generatore file CSV standard per il LIS (24 colonne).
  - `validator.py`: Validatore del codice campione a 18 caratteri e integrità dati.
  - `gui/`: Interfaccia grafica CustomTkinter (Login, Master-Detail per campioni/parametri, Finestra Configurazione Admin, Maschera Help/Guida Utente `help_dialog.py`).
- `driver_implementati/`: Documentazione tecnico-operativa approfondita per ciascun driver implementato ([README.md](file:///d:/pyprg/strumenti/driver_implementati/README.md), [dionex_ic.md](file:///d:/pyprg/strumenti/driver_implementati/dionex_ic.md), [mettler_toledo.md](file:///d:/pyprg/strumenti/driver_implementati/mettler_toledo.md), [spettrofotometro_uv_vis.md](file:///d:/pyprg/strumenti/driver_implementati/spettrofotometro_uv_vis.md)).

## Development Conventions
- Attribuzione del software: `src.__author__ = "Amboni Paolo A."`, metadati
  PEP 621 e intestazioni dei sorgenti. Il copyright FSF nel testo `LICENSE`
  resta intatto. Testo del disclaimer identico fra README e `LEGAL.md`.
- Versione reale unica in `src.__version__`, allineata a pyproject e lockfile;
  `config.app_version` restituisce la versione compilata, ignorando il vecchio
  valore modificabile nel database. GUI in sola lettura.
- Schema SQLite in `PRAGMA user_version`: migrazioni consecutive transazionali,
  prima migrazione 0→1; database futuro rifiutato prima delle scritture.
- Updater: formato manifest 1, Release stabili pubbliche dello stesso repository,
  nessun Git o token nelle postazioni distribuite. Mai sovrascrivere dati con ZIP
  di trasferimento; aggiornamenti e trasferimenti hanno pacchetti distinti.
- Ogni aggiornamento conserva backup DB, TXT transcodifiche e vecchio runtime
  fino ai controlli d'avvio. Nuovo DB solo con consenso specifico, perdendo solo
  campioni/risultati/audit e recuperando configurazione compatibile.
- Eliminazione utenti: preservare eventi, nomi, dettagli e timestamp dell'audit.
  Azzerare il riferimento nullable all'account e cancellarlo nella stessa
  transazione; rollback completo e messaggio applicativo se un vincolo o un
  errore SQLite impedisce l'operazione. Nessuna migrazione necessaria.
- Evidenza esami limitata al dettaglio: righe spuntate verdi e in grassetto;
  righe già inviate non spuntate grigie; la selezione prevale per il reinvio.
  Tag e font locali a `ExamDetail.Treeview`, senza modificare gli stili delle
  altre tabelle. La riga con focus è sottolineata, distinta dalla spunta export.
- Agilent: parsing completo prima del salvataggio; errori globali bloccanti,
  righe campione con larghezza errata scartate con avviso, soli controlli archiviati.
  Nessuna dipendenza aggiuntiva, migrazione DB o transcodifica reale precaricata.
- Sostanze LIS: `lis_substance_code` facoltativo e finale nelle dataclass e nei CRUD;
  codici memorizzati come testo, con lettere e zeri iniziali conservati. Migrazione
  nullable transazionale e ripetibile su transcodifiche e risultati, senza backfill.
- Regole complete lette insieme dal servizio di importazione; contratto dei driver
  e `get_transcoding_map()` invariati. Esame e sostanza sono salvati come snapshot;
  il merge aggiorna il valore e i codici senza riaprire gli invii già effettuati.
- L'esportatore verifica gli esami con sostanze prima di scrivere: tutte le sostanze
  del catalogo attivo corrente devono essere selezionate una sola volta. Gli esami
  esclusi sono riepilogati e registrati nell'audit; stati e conteggi si riferiscono
  soltanto alle righe scritte. Gli standard conservano il precedente tracciato.
- TXT transcodifiche `Parametro:CodiceLIS[:CodiceSostanza]`, validazione completa e
  aggiornamento atomico; coppie esame/sostanza univoche fra regole attive.
- Modulo `driver.py` rigorosamente disaccoppiato dal resto del sistema con classe base `BaseInstrumentDriver`.
- Codice campione a 18 caratteri con parsing posizionale rigoroso: Lab (1-2), Anno (3-4), Vuoto (5-6), Accettazione (7-11), Conferimento (12-14), Campione (15-18).
- Valori numerici esportati con virgola decimale e valori non numerici convertiti a `0`.
- Spostamento automatico dei file analizzati in `archiviati/` ed eventuali file errati in `errori/`.
- Unione intelligente (Merge) dei campioni duplicati: aggiunta di nuovi parametri e aggiornamento di parametri esistenti senza azzeramento o perdita di test.
- Tracciamento dello stato di esportazione LIS a livello di singolo parametro (`is_exported`, `exported_at` in `sample_results`).
- Selezione export inizializzata per tutti i campioni visibili prima di aprire i
  dettagli: soli ID pendenti al primo caricamento. Il cambio filtro conserva e
  interseca le selezioni esistenti con gli ID ancora presenti, senza aggiungerne.
  Il passaggio GUI-esportatore filtra sempre per ID; liste vuote o assenti non
  autorizzano il caricamento di altri esami. I conteggi usano gli stessi insiemi.
- Tracciamento dello stato dei campioni (`DA_ESPORTARE`, `ESPORTATO`, `ERRORE`): un campione rimane `DA_ESPORTARE` finché contiene almeno un test pendente, e passa a `ESPORTATO` solo quando tutti i suoi parametri sono stati trasmessi.
- Visualizzazione predefinita con filtro di stato 'Da Esportare' e periodo dell'ultimo mese per mostrare prioritariamente i campioni pendenti da processare, con selettori rapidi per consultare gli esportati o l'intero storico.

## Technical Constraints
- Windows x64 per installazione automatica; aggiornamenti richiedono Internet,
  uso ordinario disponibile offline. Nessun dato operativo caricato su GitHub.
- Una sola istanza per cartella; installazione automatica disabilitata quando
  esiste `.git`. Backup e staging sono esclusi dal repository e dai pacchetti.
- Il pacchetto trasferito richiede Internet per installazione/ripristino; uv,
  Python e cache sono locali alla cartella estratta. L'esecuzione avviene offline.
- Il trasferimento conserva utenti, impostazioni e transcodifiche. I quattro
  percorsi operativi vengono ricreati al primo avvio; nessun dato campione o audit
  viene distribuito. Il database sorgente non viene modificato.
- Architettura 100% locale, nessun servizio cloud o dipendenza esterna obbligatoria.
- Nessuna perdita accidentale di dati originali (i file elaborati vengono archiviati, non cancellati).

## Current Status & Active TODO
- **2026-10-20 — Major release 2.0.0**: versione effettiva, pyproject e lockfile
  allineati a 2.0.0. Note di rilascio organizzate in gestione sostanze,
  aggiornamenti, licenza/responsabilità, revisione UI e correzioni. Schema 1
  conservato, migrazione 0→1 senza perdita: nessun database nuovo necessario.
  Pubblicata la Release stabile `v2.0.0` con ZIP e manifest dopo **178 test
  superati su GitHub Windows**. Download verificato tramite il client updater:
  39 file runtime, CRC e checksum SHA-256 coerenti, nessun database incluso.
  URL: https://github.com/AmboniRider/strumentiLysa/releases/tag/v2.0.0
- **2026-10-20 — Licenza e responsabilità**: aggiunta la frase sul supporto
  operativo e sulla verifica autonoma dei risultati; autore nei metadati,
  documentazione e sorgenti. Nuova voce nel menu principale con disclaimer,
  repository e licenza integrale, disponibile per tutti senza accesso Internet.
- **2026-10-20 — Disclaimer README**: aggiunto il testo richiesto dall'utente.
  Riferimenti allineati alla licenza AGPLv3 o successiva (AGPL-3.0-or-later);
  nessuna modifica alla licenza o all'architettura durante questa attività.
- **2026-10-20 — Versione 1.2.0, aggiornamenti e backup**: motore, pannello ADMIN,
  schema versionato, recupero d'emergenza, pacchetto Release e workflow implementati.
  Il repository è ora pubblico. Nessuna pubblicazione Release eseguita in sessione;
  la prima adozione su vecchie installazioni richiede sovrapporre manualmente il
  solo pacchetto aggiornamento, preservando database e cartelle operative.
  Collaudo finale: **174 test superati**, incluso aggiornamento Windows isolato
  con uv reale, login/dashboard offline, rollback e lanciatore con runtime locale.
- **2026-10-20 — Primo accesso**: il seed verifica l'assenza dell'account `admin`
  anziché la tabella utenti vuota; controllo e creazione nella stessa transazione
  `BEGIN IMMEDIATE`. Aggiornate le istruzioni di accesso in README, manuale,
  specifiche e guida di trasferimento; aggiunte regressioni sui riavvii.
- **2026-10-16 — Eliminazione utenti corretta**: riprodotto su copia reale il
  vincolo `audit_logs.user_id` che impediva la cancellazione. Corretto
  `Database.delete_user()` con conservazione dello storico, controlli protettivi
  e gestione errori. **15 test superati** (10 nuovi e 5 database esistenti),
  incluso callback GUI. Su conferma esplicita eliminato `mascheroni` (ID 2)
  dal database operativo: 21 eventi preservati, tutti gli altri dati invariati,
  controlli di integrità e chiavi esterne superati.
- **2026-10-16 — Versione 1.1**: versione applicativa predefinita e valore
  dell'installazione locale aggiornati da 1.0 a 1.1; metadati del pacchetto,
  `src.__version__` e lockfile allineati a 1.1.0. Verificati lockfile,
  configurazione/persistenza e visualizzazione della versione nelle finestre.
- **2026-10-16 — Evidenza visiva esami**: tabella inferiore con verde chiaro
  `#E6F4EA` / testo `#1B4332` per gli spuntati, grigio tenue `#F1F3F5` / testo
  `#6B7280` per i già inviati esclusi. Legenda e sottolineatura del focus,
  aggiornamento immediato su selezione individuale/collettiva e caricamento.
  Intervento esclusivamente grafico; selezioni, database ed export invariati.
  Verifica visiva Windows con dati sintetici e 22 test esistenti superati.
- **2026-10-16 — Export selettivo verificato e corretto**: esportati soltanto
  gli ID selezionati per ciascun campione, anche senza aprire tutti i dettagli.
  Nessun recupero implicito degli esami quando la selezione è vuota o assente;
  conteggi coerenti e reinvio manuale preservato. **122 test superati in 44,96
  secondi**, inclusi 10 nuovi casi di regressione e verifiche dei CSV effettivi
  con widget reali. Database e file operativi non utilizzati durante il collaudo.
- **2026-10-15 — Agilent 5977C**: nuovo driver con esami variabili, suffisso Results
  rimosso, prime occorrenze valide conservate, prefissi configurabili e risultati
  non numerici a zero. Esito batch integrato nel servizio e nel riepilogo GUI;
  documentazione in `driver_implementati/agilent_5977c.md`, inclusa nella whitelist
  del trasferimento. Collaudo: **112 test superati in 33,90 secondi**, di cui 30
  dedicati ad Agilent; esempio con 4 campioni/36 risultati e primo cloroformio
  `0,6568`. Soltanto file e database temporanei durante le verifiche.
- **2026-10-12 — Sostanze LIS**: campo facoltativo nelle transcodifiche e nella GUI,
  persistenza nei risultati, export nelle colonne SOSTANZA/VALORE SOSTANZA,
  controllo degli esami completi e reinvio completo manuale. Nessuna associazione
  strumentale dell'esempio precaricata. Suite completa: **82 test superati** su
  Python 3.12/Windows, con test nuovi dei dialoghi e worker ttk in sottoprocessi
  isolati per evitare interferenze native Tcl/Tk durante il collaudo.
- Trasferimento: generatore ttk, backup consistente con WAL, pulizia e VACUUM
  della copia, verifica integrità ZIP e SQLite, nessuna dipendenza aggiuntiva.
- Collaudo trasferimento: 12 test dedicati, suite completa a 57 test; installer
  Internet e avvio offline verificati con runtime locale isolato. Rimane il
  collaudo operativo su una postazione Windows x64 fisicamente distinta.
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
  - Risolto nella 1.2.0: `AppWindow.update_app_title()` aggiorna soltanto il titolo,
    senza richiamare il login o ricreare la vista; regressione verificata.
  - Allineare la guida `transfer.md`: contiene riferimenti a `transer.md` inesistente e un conteggio storico di 18 test, mentre la suite attuale comprende 45 test.

### Ricognizione del 2026-10-05
- Flusso effettivo: `strumenti.bat` / `app.py` → `Database` → `AppWindow` → login → `MasterDetailView` → `ImporterService` / `LISExporter`.
- Schema SQLite: `users`, `configurations`, `transcodings`, `samples`, `sample_results`, `audit_logs`; connessioni con foreign key abilitate, WAL e chiusura deterministica. Il database operativo si trova in `data/strumenti.db`.
- Driver registrati: Dionex IC, Mettler Toledo e UV-Vis. Il driver preferito ha priorità se compatibile; seguono riconoscimento automatico e fallback. I driver dipendono dai modelli condivisi, senza accesso diretto a database o GUI.
- Importazione avviata manualmente dalla GUI; scansione non ricorsiva di `.txt`, `.csv`, `.dat`. I duplicati vengono uniti automaticamente nel flusso ordinario. Un file multi-campione viene archiviato se almeno un campione è gestito con successo, anche in presenza di altri campioni invalidi.
- L'esportazione genera un file locale CSV UTF-8, separatore `;`, 24 colonne e terminatori CRLF. Lo stato "Inviato" indica la generazione del CSV, senza conferma di ricezione da parte del LIS. I parametri senza transcodifica vengono esportati usando il nome parametro come codice esame.
- La selezione dei test vive nella GUI; l'esportatore rispetta la lista ricevuta. Dal 2026-10-16 la preselezione dei parametri pendenti è inizializzata per tutti i campioni al caricamento dell'elenco, anche senza aprire i dettagli. Il reinvio manuale dei parametri già esportati rimane possibile tramite selezione esplicita.
- Versione del pacchetto in `pyproject.toml`: `1.1.0`; versione visualizzata: impostazione `app_version` persistita nel database, default `1.1` (aggiornamento del 2026-10-16).
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


