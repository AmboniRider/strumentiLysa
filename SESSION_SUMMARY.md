# SESSION SUMMARY

## Pubblicazione major release 2.0.0 — 2026-10-20
### Decisions and Activities
- Richiesta esplicita di pubblicare la major 2.0 e sincronizzare tutte le
  modifiche locali con GitHub sul ramo `main`, comprese le attività precedenti.
- Versione 2.0.0 in `src.__version__`, pyproject e lockfile; test di installazione
  reso indipendente dalla versione corrente per verificare davvero l'upgrade
  da una copia sintetica 1.1.0 alla nuova versione.
- Riscritte le note della major attorno alle cinque novità richieste: sostanze,
  aggiornamenti, licenza, revisione interfaccia e bug fix. Chiarita la migrazione
  senza perdita e l'assenza di necessità di scaricare un database nuovo.
- Aggiornati README e guida aggiornamenti. Workflow da tag stabile impostato
  per pubblicare la Release dopo test e build, come autorizzato dall'utente;
  riferimenti delle Actions verificati sulle API ufficiali e fissati a SHA.
### Issues and Solutions
- GitHub CLI non installata localmente: pubblicazione tramite workflow GitHub
  Actions, usando il token effimero della piattaforma senza salvare credenziali.
- Verificati remoto e ramo: `origin/main` allineato prima della sincronizzazione,
  nessuna Release preesistente al controllo iniziale.
- Collaudo locale: **177 test funzionali superati** nella suite completa e
  **test di installazione Windows superato in 12.81s** dopo aver aggiornato
  il subprocess di verifica della versione corrente (178 casi verificati).
  Generato il pacchetto 2.0.0 con manifest; nessun database operativo incluso.
- Pubblicazione autorizzata mediante push di `main` e tag annotato `v2.0.0`;
  verifica finale prevista su workflow, Release pubblica, asset e allineamento Git.
- Primo workflow interrotto prima dei test: `actions/setup-python` non offre
  Python 3.12.13 su Windows 2025. Corretto usando `uv python install`, come nel
  pacchetto distribuito. Aggiunto avvio manuale per un tag esistente, con checkout
  esplicito del tag e senza riscriverne la storia.
- Verifica su clone pulito: un test storico del padding NUL leggeva file da
  `sequenze`/`archiviati`, esclusi correttamente da Git. Reso il test autonomo
  con dati sintetici in `tmp_path`; il workflow prepara fixture sintetiche per
  poter verificare anche il tag esistente senza modificarlo o pubblicare dati locali.

## Licenza, responsabilità e attribuzione — 2026-10-20
### Decisions and Activities
- Aggiunta al disclaimer la frase esatta richiesta sul supporto operativo e
  sulla verifica autonoma dei risultati prima dell'impiego professionale.
- Attribuzione `Amboni Paolo A.` in README, manuale, specifiche, metadati
  pyproject, `src.__author__` e intestazioni dei sorgenti del progetto.
  Conservati il testo integrale `LICENSE` e il relativo copyright FSF.
- `LEGAL.md` contiene autore, repository, licenza e disclaimer; il contenuto
  del disclaimer viene confrontato con README dai test per evitare divergenze.
- Nuovo `LicenseDialog` con due schede in sola lettura: informazioni complete
  e testo AGPLv3 integrale. Link GitHub aperto soltanto su clic dell'utente.
- Voce **Licenza e responsabilità** nel menu principale di `AppWindow`,
  disponibile prima del login, per OPERATORE e ADMIN e dopo il logout.
  Riutilizzata la finestra già aperta; nessun ulteriore pulsante nell'header.
- Aggiunti documento e modulo GUI alle whitelist di trasferimento e Release.
  Aggiornati contesto progetto e documentazione operativa.
### Issues and Solutions
- Testo di licenza e disclaimer vengono letti da percorsi relativi al codice,
  senza dipendere dalla directory corrente o da una connessione Internet.
  File mancanti producono un messaggio di ripristino, senza bloccare l'app.
- Test del menu principale in subprocess per evitare interferenze fra root Tk.
- Verifiche: **65 test mirati superati in 24.00s** (licenza, guida, versione,
  trasferimento e updater); **collaudo Windows reale superato in 13.15s** su copia
  senza Git, con aggiornamento, avvio offline e recupero. Superati compileall,
  `git diff --check` e `uv lock --check`; `LICENSE` invariato.
- Rigenerato il pacchetto in `dist/release-1.2.0-licenza/`: 39 file runtime,
  278232 byte, inclusi LEGAL e il nuovo dialogo. Verificati CRC e tutti i digest;
  nessuna pubblicazione effettuata. Questo pacchetto incorpora le modifiche
  successive alla precedente build in `dist/release-1.2.0/`.

## Disclaimer nel README — 2026-10-20
### Decisions and Activities
- Inserito in `README.md` il testo di esclusione di garanzia e limitazione di
  responsabilità fornito dall'utente, preservandone contenuto ed enfasi Markdown.
- Su successiva richiesta, corretti entrambi i riferimenti alla licenza:
  GNU Affero General Public License versione 3 o successiva (AGPL-3.0-or-later)
  e sezioni 15, 16 e 17 della GNU AGPLv3. File `LICENSE` invariato.
### Issues and Solutions
- Il testo fornito cita GPLv3, mentre `LICENSE` e i metadati del progetto indicano
  AGPLv3. Discrepanza inizialmente segnalata e poi risolta su richiesta dell'utente.
  Controllo `git diff --check` sui documenti aggiornati.

## Aggiornamenti GitHub e backup completi — 2026-10-20
### Decisions and Activities
- Implementato il piano concordato, preservando le modifiche locali al bootstrap
  `admin`/`admin`. Confermato tramite API che il repository è pubblico; nessuna
  Release stabile disponibile durante la verifica del nuovo client reale.
- Versione 1.2.0 allineata fra codice, pyproject e lockfile. Versione visualizzata
  in sola lettura: i vecchi valori `app_version` nel DB non alterano il confronto.
- Aggiunti motore Release/manifest e verifica ZIP/file SHA-256, controllo rete in
  background e popup una volta per avvio, pannello ADMIN con controllo manuale,
  note, installazione e backup datato tramite Online Backup API SQLite.
- Aggiunti lock di istanza, runner esterno standard-library, journal atomico,
  snapshot di programma/ambiente/database e TXT dei canali. Installazione su
  copie senza Git, uv sync bloccato, migrazione su candidato, collaudo GUI
  nascosto, rollback su errore e recupero prima degli import applicativi.
- Schema SQLite versionato con migrazioni consecutive transazionali (0→1),
  rifiuto dello schema futuro. Nuovo DB solo con consenso dedicato: recupero
  verificato di utenti/password/ruoli, impostazioni, canali completi e contatori;
  perdita dichiarata di campioni, risultati e audit. Nessun DB viene scaricato.
- Build ZIP aggiornamento distinta dal trasferimento, senza dati operativi,
  con launcher installato e manifest. Workflow Windows da tag stabile con test
  e creazione di sola bozza Release. Nessun commit/push/tag/Release pubblicata
  durante questa attività. Documentate prima adozione e pubblicazione.
- Aggiornati README, manuale, transfer, specifiche, contesto e guida UPDATES.
- Verifica finale riproducibile: TMP/TEMP in `.pytest-user-delete-uvtmp`,
  `STRUMENTI_UPDATE_E2E=1`, `uv --offline --no-cache run --no-sync python -m pytest
  -q -p no:cacheprovider --basetemp=.pytest-updates-delivery --tb=short`:
  **174 passed in 65.83s**. Collaudo su copia Windows senza Git con vero uv,
  login e campioni in dashboard offline, conservazione logica dei dati,
  recupero con Python virtuale mancante e BAT con runtime locale.
- Superati `compileall`, `git diff --check` e `uv lock --check` offline.
  Tutti i test usano database sintetici; database operativo non modificato.
- Generato `dist/release-1.2.0/strumenti-update-1.2.0.zip` con manifest:
  37 file runtime, 274622 byte. Ricontrollati CRC dell'archivio, digest ZIP e
  tutti i file; assenti database, backup e metadati Git. Artefatti pronti per
  revisione e successiva pubblicazione esplicita.
### Issues and Solutions
- La versione DB era modificabile dall'admin: sostituita con versione del codice.
- Il seed `INSERT OR IGNORE` incrementava le sequenze anche ai riavvii: ora usa
  un inserimento condizionato, preservando lo stato logico durante l'upgrade.
- Il riavvio da ambiente interrotto richiede Python base: il launcher esegue
  il recupero prima di accedere alla .venv. Runner e snapshot restano disponibili.
- Creare due root Tk nello stesso interprete di test causava errori Tcl:
  il test della finestra principale ora usa un subprocess separato; i collaudi
  grafici completi sono stati eseguiti anche fuori dalla sandbox.
- I backup e i job restano locali, ignorati da Git ed esclusi da ogni pacchetto.

## Account admin iniziale — 2026-10-20
### Decisions and Activities
- Analizzati avvio `app.py`, schema/seed SQLite, autenticazione e trasferimento.
  Il seed precedente creava `admin`/`admin` solo con tabella utenti vuota.
- Aggiornato `src/database.py`: creare `admin` con password `admin` e ruolo
  `ADMIN` quando manca quel nome, anche con altri utenti. Confronto NOCASE;
  nessun reset di password o ruolo se l'account esiste già. Controllo e
  inserimento serializzati nella stessa transazione `BEGIN IMMEDIATE`.
- Aggiornati README, manuale, specifiche, guida trasferimento e contesto progetto
  con credenziali iniziali e percorso per creare nuovi utenti.
- Test su database temporanei: credenziale iniziale valida, altri utenti
  preservati, password personalizzata e ruolo mantenuti ai riavvii anche con
  username maiuscolo. Nessun intervento sul database operativo.
- Verifica: `uv --offline --no-cache run --no-sync python -m pytest
  tests/test_database.py tests/test_user_deletion.py tests/test_transfer.py -q
  -p no:cacheprovider --basetemp=.pytest-admin-bootstrap --tb=short`, TMP/TEMP
  locali: **30 passed in 16.46s**. `git diff --check` superato.
### Issues and Solutions
- La sola presenza di altri utenti impediva il bootstrap: sostituito il
  conteggio globale con la ricerca specifica dell'account `admin`.

## Sincronizzazione GitHub — 2026-10-20
### Decisions and Activities
- Verificate le modifiche locali a database, test di eliminazione utenti e
  documentazione; preparata la pubblicazione sul ramo `main` di `origin`.
- Rieseguiti i test mirati con uv offline: **15 passed in 7.06s**.
- `git diff --check` superato; sincronizzazione senza push forzato.
### Issues and Solutions
- Scrittura dei metadati Git inizialmente limitata dalla sandbox: eseguito
  il recupero remoto con autorizzazione elevata.

## Eliminazione utenti con riferimenti nello storico — 2026-10-16
### Decisions and Activities
- Analizzati repository, `Database.delete_user()`, callback impostazioni e schema
  operativo. Il riferimento a `users` è `audit_logs.user_id`, nullable ma senza
  azione automatica di scollegamento all'eliminazione dell'account.
- Acquisita una copia consistente tramite SQLite Backup API con sorgente aperta
  in sola lettura. Riprodotto `IntegrityError: FOREIGN KEY constraint failed`
  per l'utente presente `mascheroni`, con 21 eventi collegati.
- `src/database.py`: azzeramento dei soli riferimenti nell'audit e cancellazione
  dell'account nella stessa transazione, aperta prima dei controlli protettivi.
  Conservati nome operatore, azioni, dettagli e timestamp. Gli errori SQLite
  restituiscono un esito negativo e un messaggio alla GUI dopo il rollback.
  Nessuna modifica allo schema; confermati i blocchi su auto-eliminazione e
  ultimo amministratore.
- `tests/test_user_deletion.py`: 10 casi per storico, account senza eventi,
  protezioni, secondo amministratore, rollback per ulteriori vincoli, database
  indisponibile e callback GUI nei percorsi di successo/errore.
- Verifica riproducibile: `uv --offline --no-cache run --no-sync python -m pytest
  tests/test_user_deletion.py tests/test_database.py -q -p no:cacheprovider
  --basetemp=.pytest-user-delete-check --tb=short`, con TMP/TEMP nella cartella
  locale `.pytest-user-delete-uvtmp`: **15 passed in 6.63s**.
- Collaudo della correzione sulla copia reale: comparate tutte le righe di tutte
  le tabelle, comprese le sequenze; sole differenze attese in `users` e negli ID
  dell'audit. `integrity_check=ok`, nessuna violazione in `foreign_key_check`.
- L'utente ha confermato che il nome inteso era `mascheroni`, autorizzandone la
  cancellazione reale dopo la verifica. Eseguito `delete_user(2, 1)` sul database
  già inizializzato, senza seed o migrazioni. Account eliminato; tutti i 21 eventi
  conservati con nome originale. Verificato che altri account, campioni,
  risultati, configurazioni, transcodifiche e sequenze siano rimasti invariati;
  superati anche i controlli di integrità e delle chiavi esterne sul database reale.
- Aggiornati `PROJECT_CONTEXT.md` e questo riepilogo.
### Issues and Solutions
- `mascherano` non era presente: rilevato `mascheroni` e ottenuta conferma esplicita
  dell'identità prima di intervenire sui dati reali.
- Il primo comando uv ha incontrato accesso negato al temporaneo della sandbox;
  risolto impostando TMP/TEMP in una cartella temporanea locale al progetto.

## Preparazione sincronizzazione GitHub — 2026-10-16
### Decisions and Activities
- Richiesto l'aggiornamento del repository GitHub con tutte le modifiche locali,
  inclusi versione applicativa 1.1, metadati 1.1.0, export selettivo, evidenza
  grafica, sostanze LIS, driver Agilent e aggiornamenti del trasferimento.
- Verificati ramo `main`, remoto `AmboniRider/strumentiLysa`, prerequisiti con
  `sync.bat --check` e assenza di errori con `git diff --check`.
- Pubblicazione tramite `sync.bat`: commit, fetch, merge e push ordinario;
  database, cartelle operative e materiali temporanei esclusi da `.gitignore`.
### Issues and Solutions
- Nessun conflitto o operazione Git sospesa rilevato nella verifica preliminare.
- L'esecuzione di `sync.bat` è stata respinta prima dell'avvio dalla revisione
  automatica: richiede approvazione esplicita per tutte le 32 modifiche locali
  e la pubblicazione diretta su `main`. Nessun commit o push eseguito;
  richiesta conferma dell'ambito, senza tentare percorsi alternativi.
- Successivamente l'utente ha confermato esplicitamente l'intero ambito e il
  push diretto su `main`. `sync.bat` completato: commit `6f666a0`, fetch senza
  novità da integrare e push riuscito su `AmboniRider/strumentiLysa`.
  Git ha riconosciuto la rinomina del CSV, registrando 31 file nel commit.

## Incremento versione 1.1 — 2026-10-16
### Decisions and Activities
- Su richiesta, versione applicativa avanzata da 1.0 a 1.1 e metadati Python
  allineati a 1.1.0 in `pyproject.toml`, `uv.lock` e `src/__init__.py`.
- Aggiornato `DEFAULT_APP_VERSION` in `src/config.py`; il fallback del dialogo
  impostazioni ora usa la stessa costante anziché il precedente valore letterale.
- Aggiornate le aspettative preesistenti in `tests/test_version_config.py`.
  `uv --offline --no-cache lock --check` completato con successo.
- Aggiornata soltanto la chiave `app_version` del database dell'installazione
  locale da 1.0 a 1.1, in transazione con verifica del valore precedente;
  confermato il valore persistito. Nessuna modifica ai campioni o ai risultati.
- Verifica della versione: 5 test pytest superati; il controllo esistente del
  titolo finestra è passato separatamente in un processo con un solo interprete
  Tk, verificando sia la versione iniziale 1.1 sia l'aggiornamento dinamico.
- Aggiornati `PROJECT_CONTEXT.md` e questo riepilogo. La versione locale sarà
  letta dalle finestre al prossimo avvio dell'applicazione.
### Issues and Solutions
- Eseguendo insieme i 6 test di versione, quello che crea `AppWindow` oltre alla
  root della fixture ha riscontrato errori ambientali `init.tcl` / `tk.tcl`.
  Ripetuto lo stesso controllo in isolamento, passando un contenitore di cleanup
  vuoto al posto della root aggiuntiva: finestra reale e aggiornamento verificati.
  Nessuna modifica al codice GUI per aggirare il problema dell'ambiente di test.

## Evidenza visiva degli esami — 2026-10-16
### Decisions and Activities
- Implementato il piano approvato, limitando le modifiche funzionali alla
  presentazione della tabella inferiore. Preservate le modifiche preesistenti.
- `src/gui/theme.py`: colori condivisi del dettaglio, verde `#E6F4EA` con testo
  `#1B4332`, grigio `#F1F3F5` con testo `#6B7280`.
- `src/gui/master_detail.py`: stile dedicato `ExamDetail.Treeview`, font locali,
  tag basati su spunte e stato LIS, legenda e indicazione sottolineata del focus.
  Il verde/grassetto prevale anche sugli esami già inviati selezionati per reinvio;
  gli altri già inviati restano grigi e i pendenti esclusi hanno aspetto ordinario.
- I colori si aggiornano dopo clic/Spazio, comandi collettivi, cambio campione e
  ricaricamento; nessuna modifica a database, esportatore, selezioni o comandi.
- Aggiornati `PROJECT_CONTEXT.md` e `SESSION_SUMMARY.md` per registrare il criterio
  grafico e il collaudo; nessuna nuova dipendenza e nessuna nuova API pubblica.
- Collaudo Windows con quattro stati sintetici: screenshot della sola finestra
  temporanea, verifica dei colori reali anche con focus su riga grigia e verde,
  stato Inviato conservato nel reinvio, Spazio, selezione collettiva e refresh.
  Verificata anche l'invarianza delle mappe globali Treeview e della tabella Master.
  Materiale temporaneo nella cartella ignorata `.pytest-exam-style-preview/`.
- Verifica finale: **22 test esistenti superati** relativi a selezione, export,
  merge e GUI. Comando PowerShell, ambiente già sincronizzato:
  ```powershell
  $env:TMP = Join-Path (Get-Location) '.pytest-selection-uvtmp'
  $env:TEMP = $env:TMP
  uv --offline --no-cache run --no-sync python -m pytest tests/test_selective_export.py tests/test_exporter.py tests/test_duplicate_merge.py tests/test_gui.py -q -p no:cacheprovider --basetemp=.pytest-exam-style-final --tb=short
  ```
### Issues and Solutions
- Il tema Windows sovrappone i colori della riga attiva ai tag. Rimosse le sole
  mappe di selezione dallo stile locale, mantenendo intatte quelle globali;
  sottolineata la riga con focus per distinguere il cursore dalla scelta di export.
- Le prove visive hanno usato esclusivamente campioni e database sintetici
  temporanei; nessun accesso ai campioni o alle cartelle operative.

## Esportazione dei soli esami selezionati — 2026-10-16
### Decisions and Activities
- Analizzati struttura, modello dati, selezioni Master/Detail, esportatore e
  aggiornamento degli stati SQLite; preservate le modifiche preesistenti.
- Riprodotto con widget reali e CSV temporanei il reinvio indebito di esami già
  esportati su campioni il cui dettaglio non era mai stato aperto. Prima della
  correzione, la verifica dedicata ha prodotto 3 fallimenti e 6 test superati.
- Inizializzata la selezione dei test pendenti per tutti i campioni visibili;
  campioni senza test spuntati deselezionati, conteggi allineati alle stesse
  selezioni. Aprire un dettaglio non modifica più la selezione.
- Applicato sempre il filtro per ID prima dell'esportazione. Se mancano ID
  selezionati o risultati espliciti non vengono recuperati altri esami dal DB.
  Il cambio filtro mantiene i sottoinsiemi esistenti senza includere nuovi ID.
- Conservate le scelte esplicite di reinvio e la validazione degli esami con
  sostanze: gli esami incompleti vengono esclusi, senza aggiungere sostanze.
- File modificati per questa attività:
  - `src/gui/master_detail.py`: inizializzazione, conteggi e filtro obbligatorio.
  - `src/exporter.py`: eliminazione del ripiego implicito sui risultati del DB.
  - `tests/test_selective_export.py`: regressioni sul percorso GUI → CSV → stati,
    più campioni con selezioni diverse, zero test, selezioni assenti, campioni
    esclusi, reinvio selettivo, nuovi risultati e conservazione al cambio filtro.
  - `manuale.md`, `PROJECT_CONTEXT.md`, `SESSION_SUMMARY.md`: comportamento
    aggiornato e chiusura del TODO relativo ai dettagli mai aperti.
- Collaudo eseguito esclusivamente su database e file temporanei, senza usare
  campioni o cartelle operative. Popup intercettati nei test per evitare attese.
- Suite completa: **122 test superati in 44,96 secondi**, compresi 10 nuovi casi
  di regressione; verificati anche merge, sostanze, driver, GUI e trasferimento.
  `git diff --check` senza errori di spaziatura.
- Comando riproducibile (ambiente già sincronizzato):
  ```powershell
  $env:TMP = Join-Path (Get-Location) '.pytest-selection-uvtmp'
  $env:TEMP = $env:TMP
  New-Item -ItemType Directory -Path $env:TMP -Force | Out-Null
  uv --offline --no-cache run --no-sync python -m pytest -q -p no:cacheprovider --basetemp=.pytest-selection-full --tb=short
  ```
### Issues and Solutions
- La selezione dei singoli test veniva inizializzata soltanto aprendo il dettaglio;
  il gestore export caricava tutti i risultati per i campioni senza selezione
  inizializzata. La selezione ora esiste prima di mostrare i dettagli e viene
  applicata senza eccezioni all'invio.
- I campioni completamente esportati mostravano conteggi/spunte incoerenti:
  adesso partono da zero test selezionati e richiedono una scelta esplicita di
  reinvio. I comandi che selezionano tutti i test restano disponibili.

## Driver Agilent 5977C — 2026-10-15
### Decisions and Activities
- Analizzati tracciato, driver, validatore, servizio e transcodifiche esame/sostanza.
  Concordati controlli ignorati, prima occorrenza utile, rimozione Results,
  non numerici a zero e importazione parziale per sole anomalie di larghezza riga.
- Aggiunti driver registrato, `ParsedBatch` e adattatore `parse_batch`, prefissi
  passati dal servizio, avvisi per righe scartate e messaggi dei file di soli CQ.
- Aggiornate impostazioni, riepilogo importazione e documentazione operativa.
  Modifiche preesistenti preservate; nessuna transcodifica reale precaricata,
  nessun accesso al database operativo per il collaudo.
- Inclusa la scheda Agilent nell'elenco positivo di `trasfer.py` e verificata
  la sua presenza nello ZIP, senza includere dati campione nel trasferimento.
- Verifica dedicata: **30 test superati in 4,29 secondi**. Verifica finale completa:
  **112 test superati in 33,90 secondi**, compresi GUI e trasferimento.
  Esempio: 4 campioni, 9 risultati ciascuno, cloroformio della prima occorrenza
  `0,6568`; verificati anche export standard/sostanze e merge dopo esportazione.
- Comando finale riproducibile (PowerShell, ambiente già sincronizzato):
  ```powershell
  $env:TMP = Join-Path (Get-Location) '.pytest-agilent-uvtmp'
  $env:TEMP = $env:TMP
  New-Item -ItemType Directory -Path $env:TMP -Force | Out-Null
  uv --offline --no-cache run --no-sync python -m pytest -q -p no:cacheprovider --basetemp=.pytest-agilent-final --tb=short
  ```
- File modificati per questa attività:
  - `driver.py`, `src/models.py`: driver, esito batch e adattatore retrocompatibile.
  - `src/importer_service.py`: prefissi configurati, avvisi e archiviazione dei soli CQ.
  - `src/gui/master_detail.py`, `src/gui/settings_dialog.py`: messaggi di importazione
    e descrizione/selezione del nuovo strumento.
  - `tests/test_agilent.py`: 30 test di parsing, integrazione, regressione e riepilogo.
  - `trasfer.py`, `tests/test_transfer.py`: inclusione e verifica della scheda nello ZIP.
  - `driver_implementati/agilent_5977c.md`, `driver_implementati/README.md`,
    `manuale.md`, `PROJECT_CONTEXT.md`, `SESSION_SUMMARY.md`: regole operative,
    architettura e risultati del collaudo.
### Issues and Solutions
- Il nome chimico `1,2-dicloroetano` richiede un parser CSV, non split sulla virgola.
  Usato `csv.reader(strict=True)` e completata la lettura prima di salvare dati:
  errori CSV anche tardivi annullano l'intera acquisizione.
- Un batch vuoto può essere un report valido di soli controlli: distinto con
  `archive_if_empty`; se restano solo righe campione irregolari il file va in errori.
- uv non riusciva a salvare i file temporanei nella directory della sandbox:
  impostati TMP e TEMP solo nel processo di test su una cartella ignorata del progetto.
- La whitelist di trasferimento è stata aggiornata mentre la prima suite era in
  esecuzione: il worker figlio vedeva la nuova lista, la fixture padre la precedente.
  Ripetuta l'intera suite a sorgenti stabili: tutti i 112 test superati.

## Esami LIS con sostanze — 2026-10-12
### Decisions and Activities
- Attuato il piano concordato: codice sostanza facoltativo nelle transcodifiche e
  snapshot nei risultati. Nomi strumentali distinti, codici alfanumerici come testo,
  migrazione SQLite ripetibile e coppie esame/sostanza univoche fra regole attive.
- Conservati driver, formato CSV e comportamento standard. Per le sostanze,
  TIPO ESAME conserva l'esame, SOSTANZA contiene il codice esito, VALORE SOSTANZA
  contiene il risultato e VALORE resta vuoto.
- Completezza controllata prima della scrittura rispetto al catalogo attivo corrente:
  spunte individuali, esclusione dell'intero esame incompleto, riepilogo e audit;
  esportazione degli altri esami e aggiornamento dei soli risultati scritti.
- Modifiche alle regole applicate tramite nuove importazioni o reimportazioni;
  rettifiche con stato conservato e reinvio manuale dell'esame completo.
- Esteso il TXT con terzo campo facoltativo e importazione atomica. Aggiunti campi
  in impostazioni e dettaglio; modifica per ID dal DB per conservare gli zeri iniziali.
- Aggiornati manuale, specifiche e contesto; preservate tutte le modifiche precedenti.
- Verifica finale: **82 test superati in 29,87 secondi**, inclusi 25 nuovi test
  sulle sostanze e i controlli di conservazione delle regole nel trasferimento.
  Comando: `uv --offline --no-cache run --no-sync python -m pytest -q
  -p no:cacheprovider --basetemp=.pytest-sostanze-full-final --tb=short`.
  Esecuzione con Python 3.12/Windows e runtime Tcl/Tk locale; soltanto database
  sintetici, nessuna apertura o modifica del database operativo.
- File modificati per questa funzionalità:
  - `src/models.py`, `src/database.py`, `src/importer_service.py`: campo sostanza,
    migrazione, validazione, transcodifiche TXT atomiche e snapshot dei risultati.
  - `src/exporter.py`: controllo completezza, tracciato, audit delle esclusioni e
    aggiornamento dei soli risultati scritti, anche per chiamanti senza ID risultato.
  - `src/gui/settings_dialog.py`, `src/gui/master_detail.py`: configurazione e
    visualizzazione dei codici, conservazione zeri nei dialoghi e riepilogo corretto.
  - `tests/test_substances.py`, `tests/test_transfer.py`: regressioni dei nuovi
    comportamenti, conservazione dei codici nel trasferimento e isolamento GUI.
  - `manuale.md`, `progetto.md`, `PROJECT_CONTEXT.md`, `SESSION_SUMMARY.md`:
    istruzioni operative, specifiche, architettura e risultati della verifica.
### Issues and Solutions
- Il CSV di riferimento contiene un BOM UTF-8: lettura del fixture con utf-8-sig.
- Risultati del driver senza ID: risolte corrispondenze univoche con il DB, evitando
  di marcare l'intero campione quando un suo esame viene escluso dall'export.
- Durante il collaudo combinato si sono verificati arresti nativi Tcl/Tk nel worker
  di trasferimento e nella creazione di una successiva finestra principale. Il test
  del worker passava isolatamente. Eseguiti il nuovo test dei dialoghi e quello del
  worker in sottoprocessi dedicati, mantenendo i controlli su widget e worker reali:
  la suite completa è poi passata senza arresti. Nessuna modifica al runtime GUI
  applicativo per aggirare il problema del ciclo di vita degli interpreti nei test.

## Icona applicazione — 2026-10-12
### Decisions and Activities
- Collegato `strumenti.ico` alla finestra principale e ai dialoghi figli;
  percorso indipendente dalla directory di avvio e fallback per Linux/macOS.
- Incluso l'asset nell'elenco positivo del pacchetto di trasferimento.
- Verifica del caricamento ICO in una finestra CustomTkinter temporanea senza
  database operativo; test del trasferimento: 12 superati.
### Issues and Solutions
- CustomTkinter imposta un'icona propria dopo l'avvio: la chiamata pubblica
  `iconbitmap` impedisce la sovrascrittura su Windows.
- Se l'asset manca o non è leggibile, viene emesso un warning senza bloccare la GUI.

## Pacchetto di trasferimento senza campioni — 2026-10-06
### Decisions and Activities
- Aggiunti `trasfer.py` con interfaccia ttk e `transfer.bat`; ZIP con elenco
  esplicito di sorgenti, help, licenza e configurazione runtime.
- Confermati Windows x64, installazione tramite Internet e conservazione di
  utenti, impostazioni e transcodifiche; esclusi campioni, risultati e tutti gli audit.
- Backup SQLite tramite API, cancellazioni soltanto nella copia, reset dei
  contatori e dei quattro percorsi, VACUUM e controlli integrità/foreign key.
- Generati installer e launcher dedicati: uv 0.12.14 e Python 3.12.13 locali,
  sync bloccato senza sviluppo e successivi avvii offline senza sincronizzazione.
- Riscritta la guida transfer.md; aggiornati README, contesto e ignore degli ZIP.
### Issues and Solutions
- Copiare direttamente SQLite potrebbe perdere transazioni nel WAL: usata Backup API.
- La sola cancellazione lascia dati nelle pagine libere: la copia viene ricostruita
  con VACUUM e non vengono inclusi WAL, SHM o file operativi.
- I percorsi assoluti della sorgente non valgono sulla nuova postazione: rimossi
  soltanto dalla copia, poi ricreati dal seed applicativo esistente al primo avvio.
- Le note pregresse in PROJECT_CONTEXT.md e SESSION_SUMMARY.md sono state conservate.
- Il bootstrap Windows PowerShell inizialmente caricava moduli incompatibili
  ereditati da PowerShell 7: nel BAT generato PSModulePath viene limitato ai moduli
  standard Windows, soltanto per quel processo.
- Verifica: suite completa **57 test superati**; dopo la correzione del bootstrap
  rieseguiti i **12 test di trasferimento**, tutti superati. Comandi tramite
  `uv run --no-sync --offline --cache-dir .uv-cache python -m pytest`, con database
  sintetici e basetemp locale. I test grafici hanno richiesto accesso al Tcl/Tk
  locale fuori dalla sandbox; nessun dato operativo usato.
- Eseguito realmente installa.bat nella cartella estratta di prova: scaricati uv
  e Python locali, installate quattro dipendenze runtime, Tk verificato. Successivo
  avvio offline dell'entrypoint reale con runtime isolato, account e help verificati;
  assenza di pytest nel nuovo ambiente. Il collaudo non è stato eseguito su un PC
  fisicamente distinto privo di Python.
- `git diff --check` e compilazione di trasfer.py superati.

## Aggiornamento transfer.md — 2026-10-06
### Decisions and Activities
- Revisionato integralmente [transfer.md](file:///d:/pyprg/strumenti/transfer.md) per guidare il trasferimento del software su postazioni Windows prive di Python.
- Riorganizzata la tassonomia di "Cosa copiare e cosa NON copiare" in una tabella sinottica rapida e in sezioni dettagliate categorizzate con motivazioni tecniche e rischi operativi associati (corruzione database, re-importazioni di sequenze duplicate, re-invio file LIS, rottura ambienti virtuali).
- Inclusi i nuovi componenti del repository: `sync.bat` per Git/GitHub, la cartella `driver_implementati/`, `manuale.md`, `README.md`, `LICENSE`, `agents.md`, `.gitignore` e `.gitattributes`.
- Rimosso il riferimento circolare errato `transer.md` e sostituiti i riferimenti con link diretti ai documenti del progetto.
- Aggiornato il numero di test eseguiti nella procedura di collaudo con `uv run pytest` da 18 a 45 (stato attuale della suite di test).
- Registrato lo scenario sia per trasferimento manuale (USB/ZIP) sia per clonazione diretta tramite Git (`git clone`).
### Issues and Solutions
- Nel documento originale era presente un link non funzionante a `transer.md` e il conteggio dei test era fermo alle prime versioni (18 anziché 45). Corretti entrambi e allineata la documentazione allo stato effettivo del repository.

## Authentication review — 2026-10-05
### Decisions and Activities
- Analizzati entry point, schema/CRUD utenti, hashing, sessione, login/logout, cambio/reset password, permessi GUI e documentazione (`progetto.md`, `manuale.md`, `README.md`). Nessuna modifica al codice applicativo e nessun accesso al database operativo.
- Aggiornato `PROJECT_CONTEXT.md` con il flusso di autenticazione effettivo, la separazione dall'autenticazione GitHub e i limiti rilevati.
- Verifica: `uv --offline --no-cache run --no-sync pytest -q -p no:cacheprovider tests/test_database.py --basetemp=.pytest-auth-review --tb=short`: **5 passed**. I test verificano database/seed e manutenzione con controllo ruoli; non costituiscono un audit completo del login GUI.
### Issues and Solutions
- Il connettore GitHub ha restituito 404 per il repository privato configurato nel remote; la ricerca `SessionManager` non ha restituito risultati. Analisi basata sul checkout locale al commit `cdd1e2c`, senza verificare l'allineamento remoto.
- Rilevati SHA-256 singolo, bootstrap con credenziale pubblica, controlli ruoli prevalentemente GUI, assenza di scadenza/revoca sessione e validazione password non uniforme. Registrati come aspetti da valutare, senza applicare cambiamenti funzionali fuori dallo scopo della richiesta.

## Decisions and Activities
- **2026-10-05 — Caricamento iniziale completato**: Pubblicati 54 file su `origin/main` nel repository privato `AmboniRider/strumentiLysa` (commit iniziale `60a41d2`). Ambiente virtuale, database, file operativi e cache esclusi; la cartella esistente resta la copia di lavoro collegata a GitHub.
- **2026-10-05 — Repository GitHub privato e sincronizzazione**: Creato `AmboniRider/strumentiLysa` tramite la sessione GitHub già autenticata, con visibilità Private verificata. Inizializzato Git sul ramo `main` e configurato `origin`. Aggiunti `.gitignore` per escludere ambiente, cache, credenziali e dati operativi, `.gitattributes` per i terminatori dei testi, `README.md` con istruzioni di clone/avvio e `sync.bat` con commit automatico, fetch, merge e push. Verificati elenco dei file da caricare, esclusioni e modalità `--check`.
- **2026-10-05 — Aggiornamento del manuale richiesto dall'utente**: Allineato `manuale.md` al codice per merge dei risultati già esportati, reinvio delle rettifiche, controllo della selezione per ciascun campione e significato degli stati. Corretti cartella input, nome del CSV, schema completo delle 24 colonne, normalizzazione dei valori, descrizione driver/GUI e archiviazione dei file multi-campione. Aggiornato `PROJECT_CONTEXT.md`, chiudendo il TODO documentale sul merge e registrando il punto aperto sulla selezione dei test. Verificata la guida con i test esistenti di contenuto e GUI: **5 passed** fuori dalla sandbox.
- **2026-10-05 — Ricognizione del progetto**: Letti entry point, configurazione dipendenze, driver, modelli, servizi di import/export, schema e operazioni SQLite, flussi principali della GUI, test e documentazione. Aggiornato `PROJECT_CONTEXT.md` con componenti mancanti, flusso effettivo, versione configurabile e punti da verificare. Nessun cambiamento al codice applicativo o accesso ai contenuti del database operativo. Eseguita la suite nell'ambiente esistente tramite `uv`, senza sincronizzare o scaricare pacchetti: **45 test superati** fuori dalla sandbox.
- **Intervista di Allineamento (/grill-me)**: Condotta una serie completa di domande interattive per sviscerare ogni aspetto architetturale, funzionale e di interfaccia del software:
  1. *Tipo di Interfaccia*: Scelta una Desktop GUI moderna con `CustomTkinter` per garantire usabilità immediata su postazioni di laboratorio Windows.
  2. *Flusso di Acquisizione*: Importazione manuale tramite pulsante, con scansione della cartella sorgente.
  3. *Gestione File di Origine*: Spostamento automatico dei file validati in `archiviati/` e dei file errati in `errori/` (nessuna eliminazione distruttiva).
  4. *Gestione Duplicati*: Segnalazione con prompt all'operatore per scegliere se sovrascrivere o saltare il campione già registrato.
  5. *Gestione Transcodifiche*: Tabella persistita su SQLite, modificabile dall'Admin via GUI e con supporto import/export di file `transcodifica.txt`. Avviso visivo per parametri sconosciuti.
  6. *Formato di Esportazione LIS*: Generazione automatica CSV con separatore `;`, 24 colonne fisse, virgola decimale e conversione dei non numerici in `0`. Tracciamento stato `ESPORTATO` con timestamp.
  7. *Autenticazione e Ruoli*: Ruolo `Admin` (completo con configurazioni e utenti) e `Operatore` (operativo: import/export campioni). Utente iniziale `admin`/`admin`.
  8. *Layout GUI*: Vista *Master-Detail* (tabella campioni selezionabili + griglia parametri di dettaglio del campione selezionato).
  9. *Architettura Driver*: Modulo `driver.py` isolato e basato su classi/pattern driver (`BaseInstrumentDriver`, `DionexICDriver`).
  10. *Validazione Codice Campione*: Controllo rigoroso della struttura a 18 caratteri con prefissi laboratorio configurabili.
  11. *Filtro Temporale Default*: Visualizzazione predefinita limitata ai campioni dell'ultimo mese per ottimizzare fluidità e tempi di caricamento, con selettore rapido per consultare lo storico precedente.
- **Aggiornamento Specifiche**: Riscritto completamente il file [progetto.md](file:///d:/pyprg/strumenti/progetto.md) con la specifica tecnica definitiva e dettagliata.
- **Implementazione Software Completa**:
  - *Spostamento Esempi*: Creata cartella `esempi/` con archiviazione dei file di test originali (`transcodifica.txt`, `mappatura codice campione.txt`, sequenze di test ed export CSV).
  - *Setup uv*: Creato `pyproject.toml` con dipendenze `customtkinter`, `pillow` e `pytest`; virtual environment configurato con `uv sync`.
  - *Driver Modulare*: Creato `driver.py` con `BaseInstrumentDriver` e `DionexICDriver`, isolando la logica di lettura e conversione `n.a.` -> `0` e normalizzazione decimale.
  - *Validazione & Sicurezza*: Creati `validator.py` (controllo 18 caratteri) e `auth.py` (hashing SHA-256 + salt).
  - *Database SQLite*: Creato `database.py` con tabelle relazionali, indici, seed automatico admin/admin, transcodifiche e filtri temporali.
  - *Esportazione LIS*: Creato `exporter.py` per generazione CSV a 24 colonne conforme al tracciato fisso.
  - *GUI CustomTkinter*: Creata interfaccia grafica moderna con Login, Dashboard Master-Detail, filtri temporali con default ad un mese, e dialogo impostazioni Admin.
  - *Entry Point app.py*: Implementato con ANSI terminal banner e impostazione titolo console Windows (`AGENTS.md`).
  - *Script di Lancio strumenti.bat*: Creato script batch Windows per l'avvio rapido dell'applicazione tramite doppio clic con impostazione del titolo console e codepage UTF-8.
  - *Supporto Multi-Driver & Selezione Admin*: Esteso `driver.py` con registro driver dinamico (`get_available_driver_names`, `get_driver_by_name`, `SpectrophotometerDriver`), aggiunto tab dedicato `Driver Strumento` in `SettingsDialog` protetto da controllo credenziali `Admin`, persistenza della preferenza nel DB SQLite e passaggio al servizio di importazione.
  - *Modifica Regole Transcodifica LIS*: Aggiunto supporto completo alla modifica di regole esistenti nel tab `Transcodifiche LIS` delle impostazioni:
    - Metodo `update_transcoding` in `database.py` per aggiornare una regola per ID, verificando collisioni di nomi duplicati su record distinti.
    - Pulsante dedicato `✏️ Modifica Regola` nella toolbar e supporto doppio clic sulla riga della tabella.
    - Dialogo modale precompilato con nome parametro, codice LIS e descrizione.
    - Tracciamento log di audit e notifica automatica callback di configurazione.
  - *Filtro Stato Predefinito 'Da Esportare'*: Aggiornata la toolbar della maschera principale `MasterDetailView` (`src/gui/master_detail.py`) per impostare come valore predefinito `"Da Esportare"` (con elenco opzioni ordinate: `Da Esportare`, `Esportati`, `Tutti`), garantendo che all'apertura dell'applicazione vengano mostrati immediatamente i campioni pendenti da processare ed inviare al LIS.
  - *Ordinamento Interattivo Griglie 'Transcodifiche LIS' e 'Gestione Utenti'*:
    - Implementati metodi `_on_sort_column` e `_apply_tree_sort` in `SettingsDialog` (`src/gui/settings_dialog.py`).
    - Ordinamento naturale: numerico per ID, cronologico per date, alfabetico case-insensitive per stringhe, con valori vuoti o '-' posizionati in coda.
    - Clic su intestazione colonna alterna ordinamento ascendente (▲) e discendente (▼), resettando le frecce sulle altre colonne.
    - Preservazione automatica dell'ordinamento attivo dopo operazioni di refresh (inserimento, modifica, eliminazione regola o utente).
    - Aggiunto suggerimento visuale a testo grigio sopra ciascuna griglia per informare gli utenti della funzionalità di ordinamento.
    - Protezione doppio clic: apertura del dialogo di modifica transcodifica limitata alle sole celle della tabella (`cell`, `tree`), escludendo le intestazioni.
  - *Guida al Trasferimento e Distribuzione ([transer.md](file:///d:/pyprg/strumenti/transer.md))*:
    - Redatta guida tecnica esaustiva per il deployment su nuovi PC Windows privi di ambiente Python.
    - Dettagliato il comando PowerShell standalone per installare `uv` (`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`).
    - Mappatura completa e commentata delle cartelle e dei file da copiare vs da escludere tassativamente (`.venv`, `__pycache__`, `.pytest_cache`, lock SQLite).
    - Istruzioni per `uv sync`, collaudo `uv run pytest`, avvio rapido con `strumenti.bat` e gestione di postazioni di laboratorio offline.
  - *Diagnosi Codifica & Sanitizzazione Byte Nulli (Dionex IC)*:
    - Analisi approfondita dei byte grezzi dei file in `sequenze/` (`BG2600036500010001.txt`, `BG2600036500020001.txt`, `BG2600036500030001.txt`).
    - Individuata la causa della visualizzazione anomala in Blocco Note di Windows 11: i file sono record a buffer fisso di 216 byte con padding finale di byte nulli (`\x00` / NUL). L'euristica di rilevamento senza BOM di Blocco Note scambia erroneamente la sequenza di byte nulli per UTF-16 LE, unendo le coppie di byte ASCII in ideogrammi cinesi (mojibake). Notepad++ invece rileva UTF-8/ANSI e visualizza i byte come badge `[NUL]`.
    - Aggiornato il metodo `BaseInstrumentDriver._read_text_file` in `driver.py` per rimuovere trasparentemente i byte `\x00` durante la decodifica del testo, garantendo stringhe pulite indipendentemente dal padding dello strumento.
    - Preservati inalterati i 3 file originali in `sequenze/` come da preferenza utente.
  - *Funzione di Eliminazione Campioni Esportati da Data (Solo Amministratori)*:
    - Implementato metodo `get_exported_samples_from_date` in `src/database.py` per estrarre e mostrare l'anteprima dei campioni con stato `ESPORTATO` a partire da una data specificata (ore `00:00:00`), con supporto a formati `YYYY-MM-DD`, `DD/MM/YYYY` e timestamp completi.
    - Implementato metodo `delete_exported_samples_from_date` in `src/database.py` con controllo vincolante di sicurezza sul ruolo `ADMIN` dell'utente chiamante (blocco con errore in caso di utente `OPERATORE` o sessione non valida).
    - Cancellazione a cascata automatica di tutti i parametri analitici associati nella tabella `sample_results` tramite vincolo SQLite `ON DELETE CASCADE`.
    - Preservazione rigorosa dei file fisici originali su disco (cartelle `archiviati/` ed `export/`) per garantire nessuna perdita accidentale di dati di laboratorio.
    - Tracciamento dettagliato di ogni esecuzione nel registro `audit_logs` con azione `DELETE_EXPORTED_SAMPLES`, data di riferimento e numero di campioni eliminati.
    - Aggiunta della scheda dedicata `🧹 Manutenzione Dati` nel pannello `SettingsDialog` (`src/gui/settings_dialog.py`), accessibile solo agli amministratori, provvista di scorciatoie rapide ("Oggi", "Inizio Mese", "30 Giorni Fa", "Inizio Anno"), tabella anteprima campioni coinvolti con conteggio e pulsante di eliminazione protetto da finestra modale di conferma `messagebox.askyesno`.
    - Aggiunto pulsante di accesso rapido `🧹 Elimina Esportati` nella testata della vista principale `MasterDetailView` (`src/gui/master_detail.py`), visibile esclusivamente agli utenti con ruolo `ADMIN`, che apre direttamente il dialogo impostazioni sulla scheda di manutenzione dati.
- **Verifica e Test Automatizzati**:
  - Estesa la suite di test con `test_delete_exported_samples_functionality` in `tests/test_database.py` (anteprima, rifiuto operatore, errore data invalida, eliminazione corretta per admin, cascade deletion e audit log).
  - *Driver Strumento Mettler Toledo & Supporto Multi-Campione*:
    - Condotta sessione `/grill-me` per chiarire ogni dettaglio implementativo: raggruppamento dei campioni per ID a 18 caratteri, rimozione immediata delle unità di misura nel Risultato (`293,370 uS` -> `293,370`), riconoscimento `can_handle` basato su nome `ListReport` e intestazioni, gestione duplicati interattiva per singolo campione.
    - Estesa la classe base `BaseInstrumentDriver` in [driver.py](file:///d:/pyprg/strumenti/driver.py) con il metodo `parse_samples` e aggiunta funzione `parse_instrument_samples`.
    - Implementata la classe `MettlerToledoDriver` in [driver.py](file:///d:/pyprg/strumenti/driver.py), registrata in `AVAILABLE_DRIVERS` (visibile e selezionabile anche dall'Admin nelle impostazioni della GUI).
    - Aggiornato [src/importer_service.py](file:///d:/pyprg/strumenti/src/importer_service.py) (`process_file_samples`, `import_all`, `process_single_file`) per gestire l'importazione fluida di file multi-campione, gestendo duplicati individuali e archiviazione sicura.
    - Estesa la suite di test con 5 nuovi test dedicati in [tests/test_driver.py](file:///d:/pyprg/strumenti/tests/test_driver.py) e [tests/test_mettler_integration.py](file:///d:/pyprg/strumenti/tests/test_mettler_integration.py) con esito 100% positivo (`26 passed in 2.00s`).
  - *Selezione Selettiva dei Test/Parametri per Campione*:
    - Condotta sessione `/grill-me` per chiarire ogni dettaglio: stato campione `ESPORTATO` anche con export parziale dei test, selezione test locale al campione nel pannello Detail con pulsanti 'Seleziona Tutti' e 'Deseleziona', auto-deselezione nel Master se a 0 test selezionati, colonna 'N. Parametri' con formato `X/Y` (es. `2/3`), default con tutti i test selezionati.
    - Aggiunto campo `id: Optional[int] = None` alla dataclass `ParsedResult` in `src/models.py`.
    - Popolato l'id in `Database.get_sample_results` per identificare univocamente ciascun test salvato in `sample_results`.
    - Aggiornato `LISExporter.export_samples` per supportare liste filtrate di risultati per campione (`s.results`), saltando campioni con 0 test e marcando come esportati solo quelli con righe scritte nel CSV.
    - Aggiornato `MasterDetailView` in `src/gui/master_detail.py`: aggiunta colonna `Export` (`[✓]`/`[ ]`) nel pannello Detail con supporto a doppio clic e barra spaziatrice, pulsanti 'Seleziona Tutti' e 'Deseleziona' locali al campione, sincronizzazione bidirezionale con la tabella Master (formato `X/Y` in 'N. Parametri', auto-deselezione se 0 test, auto-selezione se > 0 test), contatore dinamico dei test selezionati nel footer e filtraggio dei test all'esportazione.
    - Creata suite di test dedicata in `tests/test_selective_export.py` con 4 test (persistenza ID, export selettivo sottoinsieme parametri, esclusione campioni con 0 test, interazioni GUI e sincronizzazione bidirezionale).
    - Suite completa passata con successo (`30 passed in 2.59s`).
  - *Unione Intelligente dei Campioni Duplicati (Merge) & Tracciamento Esportazione LIS per Parametro*:
    - Condotta sessione interattiva `/grill-me` per chiarire ogni dettaglio architetturale relativo ai campioni duplicati con test aggiuntivi o non inviati in precedenza:
      1. *Comportamento di Base*: Applicazione dell'unione intelligente (Merge), aggiungendo nuovi parametri al campione esistente e aggiornando i parametri coincidenti con il nuovo valore analitico.
      2. *Gestione Esportazione Test Precedenti*: Tracciamento per singolo parametro (`is_exported`, `exported_at`); se un campione già esportato riceve nuovi test, il campione torna `DA_ESPORTARE` e propone di default solo i nuovi test. I test già inviati rimangono considerati `Inviati` (nessuna rettifica automatica accidentale al LIS).
      3. *Esperienza Utente in Importazione*: Integrazione automatica fluida senza popup continui per singolo duplicato; riepilogo finale dettagliato con il numero di campioni integrati con nuovi test.
      4. *Rappresentazione GUI*: Colonna visuale "Stato LIS" (`🟢 Inviato` / `🟠 Da Inviare`) nella griglia di dettaglio parametri, pre-spunta `[✓]` attiva solo sui parametri da inviare e facoltà per l'operatore di spuntare manualmente anche quelli inviati se desidera una rettifica.
      5. *Stato Campione su Esportazione Parziale*: Il campione rimane `DA_ESPORTARE` finché restano parametri da inviare, passando a `ESPORTATO` solo quando tutti i parametri risultano trasmessi.
    - Esteso `src/models.py`: aggiunti campi `is_exported: bool = False`, `exported_at: Optional[str] = None` in `ParsedResult` e `pending_results_count: int = 0` in `SampleRecord`.
    - Aggiornato `src/database.py`:
      - DDL e migrazione automatica retrocompatibile per aggiungere `is_exported` e `exported_at` alla tabella `sample_results`.
      - Aggiornato `save_sample_with_results` con logica di merge parametro per parametro.
      - Aggiunto metodo `mark_results_as_exported(result_ids, sample_ids, filename)` per aggiornare selettivamente i singoli test inviati e aggiornare lo stato del campione a `ESPORTATO` solo se non ha più test pendenti.
      - Aggiornato `get_samples` per includere `pending_results_count`.
    - Aggiornato `src/importer_service.py`: conteggio `merged_count` nel riepilogo `ImportBatchSummary` e merge automatico durante l'elaborazione dei campioni.
    - Aggiornato `src/exporter.py`: passaggio dei soli `exported_result_ids` alla persistenza del database.
    - Aggiornato `src/gui/master_detail.py`: visualizzazione della nuova colonna "Stato LIS", preselezione intelligente dei soli test non esportati e riepilogo import arricchito.
    - Creata suite di test dedicata in `tests/test_duplicate_merge.py` e centralizzata la fixture `ctk_root` con scope di sessione in `tests/conftest.py`.
    - Suite completa passata con successo (`34 passed in 2.88s`).
  - *Documentazione dei Driver Implementati (`driver_implementati/`)*:
    - Condotta sessione di intervista `/grill-me` per allineare formato, struttura e livello di dettaglio della documentazione.
    - Creata cartella `driver_implementati/` con schede complete tecnico-operative e indice comparativo:
      - `README.md`: panoramica comparativa degli strumenti, matrice delle caratteristiche e ciclo di vita del driver.
      - `dionex_ic.md`: specifiche per Cromatografo Ionico Dionex/IC (anioni, delimitatore tab, gestione padding NUL 216 byte, estrazione codice campione e normalizzazione `n.a.` -> `0`).
      - `mettler_toledo.md`: specifiche per Titolatore Mettler Toledo (file multi-campione `ListReport.csv`, separatore `;`, raggruppamento per ID e rimozione automatica unità di misura come `uS`).
      - `spettrofotometro_uv_vis.md`: specifiche per Spettrofotometro UV-Vis/Assorbanza (delimitatori multipli, estrazione ID campione da nome file, normalizzazione fotometrica).
  - *Manuale Utente (`manuale.md`) e Maschera Interattiva di Aiuto (`HelpDialog`)*:
    - Condotta sessione `/grill-me` per allineare layout e requisiti: concordata una maschera modale con indice capitoli a sinistra (TOC) e visualizzatore formattato a destra con ricerca testuale rapida; collocazione del file `manuale.md` nella radice del progetto.
    - Redatto il manuale operativo completo [manuale.md](file:///d:/pyprg/strumenti/manuale.md) strutturato in 10 capitoli: introduzione, strumenti e formati, interfaccia grafica, workflow operativo, guida pratica a selezione/deselezione (doppio clic, tasto Spazio, pulsanti globali e dedicati al campione, sincronizzazione `X/Y`), gestione duplicati e unione intelligente (Smart Merge), tabella legenda stati, formato tracciato LIS CSV a 24 colonne, funzioni amministrative (transcodifiche, driver, utenti, eliminazione esportati) e sezione FAQ.
    - Sviluppata la classe `HelpDialog` in `src/gui/help_dialog.py` (`CTkToplevel`) con parsing automatico dei titoli H2 markdown, generazione dinamica dei pulsanti dell'indice laterale, salto immediato alla sezione con evidenziazione temporanea, motore di ricerca in tempo reale con conteggio delle occorrenze, navigazione e pulizia dei filtri, e gestione resiliente del fallback in caso di file assente.
    - Integrato il pulsante `❓ Guida` nell'header di `MasterDetailView` (`src/gui/master_detail.py`) collocato accanto al pulsante password e reso accessibile a tutti gli utenti senza distinzione di ruolo (`OPERATORE` e `ADMIN`).
    - Creata suite di test automatizzati `tests/test_help.py` (5 test) per verificare completezza dei capitoli, inizializzazione interfaccia, navigazione indice, ricerca testuale, fallback e visibilità del pulsante per entrambi i ruoli.
    - *Formalizzazione Licenza GNU AGPLv3*:
    - Scaricato e integrato il testo ufficiale della licenza GNU AGPLv3.0 nel file [LICENSE](file:///d:/pyprg/strumenti/LICENSE).
    - Aggiornato [pyproject.toml](file:///d:/pyprg/strumenti/pyproject.toml) con `license = { file = "LICENSE" }`, classifiers standard OSI per AGPLv3+, e configurato `[dependency-groups]` per uv in modo che `uv sync` mantenga sincronizzato sia l'ambiente di runtime che di test.
    - Aggiunto l'header SPDX `# SPDX-License-Identifier: AGPL-3.0-or-later` e nota di copyright in testa a tutti i 18 moduli sorgente Python del progetto.
    - Aggiornate le specifiche di progetto [progetto.md](file:///d:/pyprg/strumenti/progetto.md) e il manuale utente [manuale.md](file:///d:/pyprg/strumenti/manuale.md).
    - Eseguita la suite completa di 45 test con `uv run pytest`, confermando l'integrità del software al 100%.

## Issues and Solutions
- **2026-10-05 — GitHub CLI e proprietà Git**: `gh` non è installata; creazione repository effettuata via browser con la skill computer-use. La prima inizializzazione Git nella sandbox ha creato metadati con proprietà dell'utente sandbox, causando `dubious ownership`. Conservata la sola directory iniziale dei metadati in `.git-sandbox-backup/` (ignorata) e ricreato Git con l'utente Windows reale tramite esecuzione autorizzata, senza cambiare configurazioni globali o cancellare file del progetto.
- **2026-10-05 — Manuale allineato**: Risolta la discrepanza sul valore dei risultati già esportati dopo il merge e sostituito lo schema CSV documentato con le intestazioni effettive. Precisato che l'applicazione genera il file e non verifica la ricezione del LIS; documentato il controllo del dettaglio prima dell'esportazione per gestire la selezione dei test con il comportamento attuale. I punti funzionali restano da verificare separatamente; nessuna modifica al codice.
- **2026-10-05 — Ambiente di test**: La prima esecuzione nella sandbox ha superato 32 test e prodotto 13 errori nella fixture GUI (`Can't find a usable init.tcl`), oltre a warning per accesso negato alla cache pytest. La ripetizione autorizzata fuori dalla sandbox, con cache pytest disabilitata, ha superato tutti i 45 test. Non è stato necessario modificare Python o Tcl/Tk.
- **2026-10-05 — Discrepanze documentali e punti aperti**: Rilevata divergenza tra manuale e codice/test sul valore dei parametri già esportati dopo un merge; rilevati riferimenti a `transer.md` inesistente e conteggio test obsoleto nella guida di trasferimento. Corretto il riferimento in `PROJECT_CONTEXT.md` e registrati gli altri allineamenti come TODO. Segnalato anche il richiamo a `show_login()` nell'aggiornamento del titolo finestra, da verificare durante una sessione autenticata. Nessuna correzione funzionale applicata, dato che la richiesta riguarda la comprensione del progetto.
- **Issue**: `UnicodeEncodeError: 'charmap' codec can't encode characters` durante la stampa dei caratteri grafici del banner ANSI su Windows console con codifica legacy cp1252.
- **Solution**: Aggiunta la riconfigurazione automatica di `sys.stdout` e `sys.stderr` in UTF-8 all'avvio con fallback grafico ASCII in caso di console restrittive.
- **Issue**: `sqlite3.DatabaseError: database disk image is malformed` durante l'esecuzione di test multipli consecutivi con database SQLite in modalità WAL su Windows, causato da connessioni non chiuse esplicitamente da `with conn:`.
- **Solution**: Convertito `Database.get_connection()` in un context manager `@contextmanager` con blocco `try-finally` che garantisce la chiusura deterministica `conn.close()` e il commit automatico di ogni transazione.
- **Issue**: File esportati dallo strumento con padding di byte nulli (`0x00`) fino a 216 byte interpretati come UTF-16 LE da Blocco Note Windows 11 con caratteri strani e potenziale inserimento di byte nulli nel database/parsing.
- **Solution**: Inserita la rimozione automatica dei byte `\x00` in `BaseInstrumentDriver._read_text_file`, sanificando le stringhe prima di qualunque operazione di parsing e validazione.
- **Issue**: Errore `_tkinter.TclError: couldn't read file "scale.tcl"` o `invalid command name "tcl_findLibrary"` durante l'esecuzione dell'intera suite di test pytest su Windows, causato dalla distruzione e ricreazione multipla dell'interprete Tcl/Tk (`root.destroy()`) in moduli di test consecutivi.
- **Solution**: Centralizzata la fixture `ctk_root` in `tests/conftest.py` con `@pytest.fixture(scope="session")`, eliminando le istanziazioni multiple per-modulo e garantendo stabilità assoluta all'interprete Tcl su Windows.
- **Issue**: Nel test di esportazione, se un campione ha una lista vuota di parametri `s.results = []`, la condizione `if s.results` in `LISExporter.export_samples` falliva e ricaricava tutti i parametri dal DB sovrascrivendo l'esclusione.
- **Solution**: Sostituita la condizione con `if s.results is not None: results = s.results`, garantendo che una lista vuota o parziale esplicitamente passata venga rispettata e che campioni con 0 parametri vengano ignorati senza generare righe nel CSV.
- **Issue**: `sqlite3.OperationalError: no such column: is_exported` durante l'esecuzione di `init_db()` su database SQLite preesistenti privi della colonna `is_exported`, dovuto alla creazione dell'indice `idx_results_is_exported` prima dell'esecuzione delle istruzioni `ALTER TABLE`.
- **Solution**: Anticipata la verifica `PRAGMA table_info` e la migrazione delle colonne `is_exported` ed `exported_at` prima della dichiarazione `CREATE INDEX`, consentendo una migrazione fluida e trasparente dei database esistenti.
- **Issue**: Il test `test_settings_dialog_version_save_and_propagation` in `tests/test_version_config.py` si bloccava in attesa interattiva su Windows a causa dell'apertura del pop-up modale `tkinter.messagebox.showinfo`.
- **Solution**: Applicato `monkeypatch` su `tkinter.messagebox.showinfo` e `tkinter.messagebox.showwarning` nei test interessati, consentendo un'esecuzione automatizzata non bloccante.




