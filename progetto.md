# SPECIFICHE DI PROGETTO: INTERFACCIA STRUMENTI DI LABORATORIO - LIS

**Autore:** Amboni Paolo A.

---

## 1. SCOPO E OBIETTIVI DEL PROGETTO

Il progetto consiste nella realizzazione di un'applicazione software desktop in Python finalizzata all'interfacciamento tra gli strumenti di laboratorio (es. Cromatografo Ionico Dionex / IC e futuri strumenti analitici) e il sistema informativo del laboratorio (**LIS** - *Laboratory Information System*).

### Obiettivi Primari:
1. **Acquisizione ed Elaborazione**: Importare in modo controllato i file di testo prodotti dagli strumenti analitici, validando i dati e archiviando automaticamente i file elaborati.
2. **Architettura Driver Modulare**: Isolare tutta la logica di parsing e conversione specifica di ogni strumento in un singolo file denominato `driver.py`, consentendo l'integrazione immediata di nuovi strumenti senza toccare il resto dell'applicazione.
3. **Normalizzazione e Transcodifica**: Mappare i nomi dei parametri dello strumento nei codici esame standard recepiti dal LIS tramite una tabella di transcodifica gestibile da interfaccia grafica e persistita su database.
4. **Persistenza Locale**: Salvare campioni, parametri, utenti, configurazioni e storico esportazioni in un database locale **SQLite**.
5. **Interfaccia Grafica Moderna (GUI)**: Fornire una dashboard desktop con layout *Master-Detail* (CustomTkinter) per la visualizzazione, filtraggio, selezione ed esportazione dei campioni.
6. **Esportazione per LIS**: Generare file CSV strutturati e conformi al tracciato fisso richiesto dal LIS, tracciando lo stato dei campioni esportati.
7. **Controllo degli Accessi**: Gestire l'autenticazione con ruoli differenziati (**Admin** e **Operatore**).

---

## 2. STACK TECNOLOGICO E LINEE GUIDA DI SVILUPPO

- **Linguaggio**: Python 3.11+
- **Gestione Ambiente e Dipendenze**: `uv` (utilizzo di `pyproject.toml` / `uv.lock` e comandi `uv sync`, `uv run`)
- **Interfaccia Grafica**: `CustomTkinter` (interfaccia moderna, reattiva, con supporto temi Dark/Light)
- **Database**: `SQLite 3` (locale, embedded, zero-configurazione)
- **Sistema Operativo Target**: Windows (con codice multipiattaforma compatibile Linux/macOS)
- **Licenza Software**: GNU Affero General Public License v3 o successiva (`AGPL-3.0-or-later`, vedi file [LICENSE](file:///d:/pyprg/strumenti/LICENSE))
- **Convenzioni Terminale (come da `AGENTS.md`)**:
  - Banner di avvio grafico con cornice ANSI colorata.
  - Impostazione dinamica del titolo della console terminale.

---

## 3. SPECIFICHE DEL CODICE CAMPIONE (18 CARATTERI)

Il collegamento univoco tra i sistemi è garantito dal **Codice Campione** a 18 caratteri generato dal LIS e inserito nella programmazione dello strumento.

### 3.1 Struttura Posizionale del Codice Campione
| Posizione (1-based) | Lunghezza | Campo | Descrizione / Valori Ammessi | Esempio (`BG2600104420010001`) |
|---|---|---|---|---|
| **1 - 2** | 2 car. | **Laboratorio** | Codice identificativo sede (`BG`, `MI`, `BS`, `RL`, `VP`, `MN`, `MB`) | `BG` (Bergamo) |
| **3 - 4** | 2 car. | **Anno** | Ultime due cifre dell'anno (numerico) | `26` -> 2026 |
| **5 - 6** | 2 car. | **Vuoto / Filler** | Costante fissa `00` | `00` |
| **7 - 11** | 5 car. | **Accettazione** | Numero progressivo accettazione (numerico a 5 cifre) | `10442` |
| **12 - 14** | 3 car. | **Conferimento** | Numero conferimento (numerico a 3 cifre con zeri iniziali) | `001` -> 1 |
| **15 - 18** | 4 car. | **Campione** | Numero campione (numerico a 4 cifre con zeri iniziali) | `0001` -> 1 |

### 3.2 Regole di Validazione
- Il codice deve avere una lunghezza esatta di 18 caratteri.
- I primi 2 caratteri devono appartenere all'elenco dei laboratori abilitati (configurabile).
- I caratteri dal 3 al 18 devono essere rigorosamente numerici.
- I caratteri 5-6 devono corrispondere a `00`.
- Se un file contiene un codice non valido, l'importazione del file fallisce: il file viene spostato nella cartella `errori` e viene generata una notifica nella GUI.

---

## 4. FORMATO DEI FILE DELLO STRUMENTO (ACQUISIZIONE)

### 4.1 Caratteristiche del File dello Strumento Corrente (Cromatografo Ionico Dionex / IC)
- **Posizione**: Cartella di ingresso configurata (default: `./sequenze/`).
- **Nome File**: `<CODICE_CAMPIONE>.txt` (es. `BG2600104420010001.txt`).
- **Separatore di campo**: Tabulazione (`\t`).
- **Struttura interna del file**:
  - **Riga 1**: Contiene l'etichetta `Sample Name:` seguita dal codice campione a 18 caratteri (es. `Sample Name:\tBG2600104420010001`).
  - **Righe 2 - 8**: Righe vuote o metadati dello strumento.
  - **Riga 9**: Intestazione della tabella parametri (es. `Component\tAmount `).
  - **Righe 10 - 11**: Righe di spaziatura/separatore.
  - **Righe 12+**: Parametri analitici con relativo valore (es. `Fluoruri\tn.a.`, `Cloruri\t0,7733`, `Nitrati\t8,6948`, `Solfati\t3,8142`).

### 4.2 Flusso di Acquisizione & Gestione Cartelle
1. **Trigger di Importazione**: L'operatore preme il pulsante **"Carica / Importa File"** nella GUI.
2. **Lettura e Parsing**: Il software scansiona la cartella di ingresso, invoca il driver specifico per ciascun file ed effettua la validazione.
3. **Gestione Post-Importazione dei File**:
   - **File Elaborati con Successo**: Vengono spostati automaticamente nella sottocartella `archiviati/` (o percorso configurato).
   - **File con Errori di Formato/Validazione**: Vengono spostati automaticamente nella sottocartella `errori/` e segnalati all'utente.
4. **Gestione Duplicati**: Se un codice campione è già presente nel database SQLite, viene mostrato un prompt di conferma all'operatore per scegliere se:
   - *Sovrascrivere* i risultati esistenti con i nuovi valori.
   - *Saltare* il file lasciando invariati i dati precedenti.

---

## 5. ARCHITETTURA DEI DRIVER (`driver.py`)

Tutta la logica di lettura, parsing e conversione dei file generati dagli strumenti risiede esclusivamente nel file `driver.py`.

### 5.1 Requisiti di Modularità
- Definizione di una classe base astratta/interfaccia `BaseInstrumentDriver` con metodi standard:
  - `can_handle(filepath: Path) -> bool`: verifica se il file è gestibile da questo driver.
  - `parse_file(filepath: Path, transcoding_map: dict) -> ParsedSample`: estrae metadati del campione e lista dei parametri con valori numerici/normalizzati.
- Implementazione della classe concreta `DionexICDriver` (Cromatografo Ionico Dionex / IC) e supporto per driver addizionali (es. `SpectrophotometerDriver`).
- Funzione factory standard `get_driver(filepath, preferred_driver_name)` e `parse_instrument_file(filepath, transcoding_map, driver_name)` utilizzata dal resto dell'applicazione.
- **Supporto Multi-Strumento e Driver di Default**: Nel caso siano presenti o implementati più strumenti, l'interfaccia di configurazione consente all'utente **Admin** di selezionare il driver predefinito da utilizzare durante l'acquisizione dei file. La scelta viene salvata a database e applicata al servizio di importazione.
- L'aggiunta di un nuovo strumento (es. Spettrofotometro, ICP, HPLC) richiederà **solo** l'implementazione della nuova classe driver all'interno di `driver.py` e la sua registrazione nella lista `AVAILABLE_DRIVERS`.

---

## 6. GESTIONE DELLA TABELLA DI TRANSCODIFICA

La tabella di transcodifica associa il nome del parametro prodotto dallo strumento al codice esame ufficiale del LIS e, facoltativamente, a un codice sostanza LIS. Ogni sostanza ha un nome strumentale distinto; più parametri possono condividere lo stesso codice esame con sostanze differenti.

### 6.1 Esempio di Mappatura
| Parametro Strumento | Codice Esame LIS | Descrizione Parametro |
|---|---|---|
| `Fluoruri` | `BG00594` | Fluoruri |
| `Cloriti` | `BG00589` | Cloriti |
| `Cloruri` | `BG00590` | Cloruri |
| `Nitriti` | `BG00596` | Nitriti |
| `Clorati` | `BG00588` | Clorati |
| `Nitrati` | `BG00595` | Nitrati |
| `Solfati` | `BG00603` | Solfati |

### 6.2 Regole di Gestione
- I dati di transcodifica sono salvati e mantenuti nella tabella `transcodings` del database SQLite.
- L'amministratore può aggiungere, modificare o eliminare voci direttamente dalla scheda **Configurazione** della GUI.
- È supportata la funzione di importazione/esportazione da file di testo (`transcodifica.txt`, formato `Parametro:CodiceLIS[:CodiceSostanza]`). Le righe a due campi configurano esami standard. La validazione dell'intero file e l'applicazione transazionale impediscono importazioni parziali in caso di errori o duplicati.
- Il codice sostanza è testo alfanumerico facoltativo: gli spazi esterni sono eliminati, lettere e zeri iniziali conservati. Le coppie esame/sostanza delle regole attive sono univoche, anche tramite indice SQLite parziale.
- L'importazione legge insieme le regole complete, passa ai driver la mappa di stringhe attuale e conserva nel risultato i codici esame e sostanza. Le modifiche alle regole si applicano solo a importazioni/reimportazioni successive.
- **Parametri non mappati**: Se nel file dello strumento compare un parametro non presente nella tabella di transcodifica, il software visualizza un avviso visivo nella GUI, consentendo all'Admin di mapparlo rapidamente o all'operatore di escluderlo.

---

## 7. FORMATO E REGOLE DI ESPORTAZIONE PER IL LIS

### 7.1 Caratteristiche del File di Export
- **Formato**: File CSV con codifica UTF-8.
- **Separatore di campo**: Punto e virgola (`;`).
- **Destinazione predefinita**: Cartella `export/` (configurabile).
- **Nome File Generato**: `ESPORTAZIONE_YYYYMMDD_HHMMSS.csv` (es. `ESPORTAZIONE_20260831_102323.csv`).

### 7.2 Intestazione Fissa CSV (24 Colonne)
```csv
ANNO;ACCETTAZIONE;CONFERIMENTO;CAMPIONE;ALIQUOTA;UNITÀ CAMPIONARIA;N. RISULTATO;SEGNO;VALORE;RISULTATO;TIPO ESAME;ESITO;UNITÀ BGSURA;DATA INIZIO;DATA FINE;SOSTANZA;RISULTATO SOSTANZA;VALORE SOSTANZA;SEGNO SOSTANZA;INCERTEZZA SOSTANZA;GERME;RILEVATO GERME;VALORE GERME;CODICE CAMPIONE
```

### 7.3 Regole di Valorizzazione dei Campi
| N° | Colonna | Obbligatorio | Regola di Calcolo / Valore | Esempio |
|---|---|---|---|---|
| 1 | **ANNO** | Sì | 4 cifre calcolate dalle posizioni 3-4 del codice campione (`26` -> `2026`). | `2026` |
| 2 | **ACCETTAZIONE** | Sì | Valore estratto dalle posizioni 7-11 del codice campione. | `10442` |
| 3 | **CONFERIMENTO** | Sì | Valore estratto dalle posizioni 12-14 del codice campione, senza zeri iniziali (`001` -> `1`). | `1` |
| 4 | **CAMPIONE** | Sì | Valore estratto dalle posizioni 15-18 del codice campione, senza zeri iniziali (`0001` -> `1`). | `1` |
| 5 | **ALIQUOTA** | No | Vuoto | `` |
| 6 | **UNITÀ CAMPIONARIA** | No | Vuoto | `` |
| 7 | **N. RISULTATO** | No | Vuoto | `` |
| 8 | **SEGNO** | No | Vuoto | `` |
| 9 | **VALORE** | Standard | Valore numerico normalizzato con virgola decimale, o `0` per non numerici. Vuoto nelle righe con sostanza. | `0,7733` o `0` |
| 10 | **RISULTATO** | No | Vuoto | `` |
| 11 | **TIPO ESAME** | Sì | Codice esame LIS ottenuto dalla tabella di transcodifica. | `BG00590` |
| 12 | **ESITO** | No | Vuoto | `` |
| 13 | **UNITÀ BGSURA** | No | Vuoto | `` |
| 14 | **DATA INIZIO** | No | Vuoto | `` |
| 15 | **DATA FINE** | No | Vuoto | `` |
| 16 | **SOSTANZA** | Per sostanze | Codice sostanza LIS salvato nel risultato; vuoto per standard. | `50010` |
| 17 | **RISULTATO SOSTANZA** | No | Vuoto | `` |
| 18 | **VALORE SOSTANZA** | Per sostanze | Valore normalizzato del risultato; vuoto per standard. | `50,60` |
| 19 | **SEGNO SOSTANZA** | No | Vuoto | `` |
| 20 | **INCERTEZZA SOSTANZA**| No | Vuoto | `` |
| 21 | **GERME** | No | Vuoto | `` |
| 22 | **RILEVATO GERME** | No | Vuoto | `` |
| 23 | **VALORE GERME** | No | Vuoto | `` |
| 24 | **CODICE CAMPIONE** | Sì | Codice campione completo a 18 caratteri. | `BG2600104420010001` |

### 7.4 Tracciamento dello Stato dei Campioni e Gestione Storico
- **Completezza degli esami con sostanze**: prima di scrivere il CSV, l'esportatore raggruppa le sostanze selezionate per campione e codice esame. I codici selezionati devono coincidere con tutte le sostanze delle transcodifiche attive correnti, una sola riga per codice. Un gruppo incompleto, duplicato o fuori catalogo viene saltato interamente; gli altri esami vengono esportati. Le spunte restano individuali e gli standard conservano il comportamento precedente.
- **Esclusioni e conteggi**: il riepilogo e l'audit `EXPORT_LIS_SKIPPED` riportano campione, esame e motivi. Solo i risultati scritti cambiano stato; se non vi sono righe ammissibili, non si crea il CSV. Una rettifica mantiene gli stati precedenti e richiede un reinvio manuale dell'esame completo.
- Ogni riga/campione esportato viene aggiornato nel database con:
  - Stato: `ESPORTATO`
  - Data e Ora di esportazione
  - Nome del file di esportazione generato
- **Filtro Temporale Predefinito (Ultimo Mese)**:
  - Poiché il volume dei campioni esportati nel tempo può diventare considerevole, per mantenere l'interfaccia scattante e focalizzata sull'operatività corrente, la vista dei campioni carica di **default solo i campioni dell'ultimo mese** (ultimi 30 giorni).
  - L'operatore può facilmente modificare o estendere il filtro temporale tramite un selettore rapido (es. *Ultimi 7 giorni*, *Ultimo Mese [Default]*, *Ultimi 3 Mesi*, *Anno Corrente*, *Tutti / Intervallo Personalizzato*) per consultare, ricercare o riesportare campioni storici più datati.
- **Filtro di Stato**: L'operatore può filtrare i campioni per visualizzare: *Tutti*, *Solo da esportare (nuovi)*, *Già esportati*.
- L'operatore può riselezionare e riesportare campioni già esportati in caso di necessità.

---

## 8. AUTENTICAZIONE E GESTIONE UTENTI

### Aggiornamenti amministrativi e backup

La versione effettiva è `src.__version__`, non modificabile dalle impostazioni.
Il controllo asincrono delle Release GitHub stabili informa tutti gli utenti;
solo ADMIN può installare da **Impostazioni → Aggiornamenti e backup** o avviare
una copia completa verificata del database. L'installazione usa ZIP senza dati,
manifest con compatibilità e checksum, processo esterno e rollback.
Lo schema è versionato tramite `PRAGMA user_version` e migrazioni consecutive.
La politica database è esplicita per Release: conservazione, migrazione senza
perdita o nuovo DB con conferma, backup, esportazione dei canali e recupero di
utenti, impostazioni e transcodifiche. Dettagli del protocollo: [UPDATES.md](UPDATES.md).

### 8.1 Modello di Sicurezza
- Autenticazione basata su credenziali memorizzate su database SQLite.
- Password salvate con hashing sicuro (SHA-256 con salt per ciascun utente).
- Utente predefinito creato all'avvio se manca l'account `admin`, anche se
  esistono altri utenti (confronto senza distinzione di maiuscole/minuscole):
  - **Username**: `admin`
  - **Password**: `admin`
  - **Ruolo**: `Admin`
- Se l'account esiste già, password e ruolo vengono conservati. Dopo il primo
  accesso è possibile creare utenti in **Impostazioni → Gestione Utenti** e
  cambiare la password iniziale tramite **Password**.

### 8.2 Ruoli e Permessi
1. **Ruolo Admin**:
   - Accesso a tutte le funzioni operative (Importa, Visualizza, Seleziona, Esporta).
   - Accesso alla scheda **Configurazione**:
     - Selezione del Driver di Default per gli strumenti di laboratorio.
     - Gestione Utenti: creazione, cambio ruolo, reset password, cancellazione.
     - Gestione Percorsi Cartelle (Input, Archivio, Errori, Export).
     - Gestione Tabella Transcodifiche (CRUD, Import/Export file).
     - Gestione Codici Laboratorio abilitati.
2. **Ruolo Operatore**:
   - Accesso alla schermata operativa (Importazione file, Visualizzazione campioni e parametri, Selezione ed Esportazione LIS).
   - Modifica della propria password personale.
   - Nessun accesso alle schede di configurazione di sistema o alla selezione dei driver.

---

## 9. INTERFACCIA UTENTE (GUI CUSTOMTKINTER)

L'applicazione presenta un'interfaccia a finestra desktop strutturata in due sezioni principali:

### 9.1 Schermata di Login
- Campi Username e Password con validazione.
- Selezione tema (Dark / Light).
- Accesso diretto alla dashboard principale con interfaccia profilata in base al ruolo.

### 9.2 Schermata Principale (Layout Master-Detail)
- **Barra Superiore**:
  - Logo/Titolo dell'applicazione.
  - Indicatore utente attivo e badge del ruolo (`Admin` / `Operatore`).
  - Pulsante **Impostazioni / Configurazione** (abilitato solo per Admin).
  - Pulsante **Profilo / Cambio Password**.
  - Pulsante **Logout**.
- **Barra Controlli & Filtri**:
  - Pulsante principale **"Carica / Importa Nuovi File"**.
  - Casella di ricerca testuale (filtro per codice campione, accettazione, laboratorio).
  - Selettore stato: `Tutti` | `Da Esportare` | `Esportati`.
  - **Filtro Temporale**: Selettore rapido con default a **"Ultimo Mese"** (opzioni: *Ultimi 7 Giorni*, *Ultimo Mese (Default)*, *Ultimi 3 Mesi*, *Anno Corrente*, *Tutti* / *Personalizzato*) per gestire agevolmente volumi elevati di campioni storici.
  - Checkbox per selezione massiva: `Seleziona Tutti` | `Deseleziona Tutti`.
- **Pannello Master (Elenco Campioni)**:
  - Tabella interattiva dei campioni con colonne:
    - *Selezione (Checkbox)*
    - *Codice Campione (18 car.)*
    - *Laboratorio*
    - *Anno*
    - *Accettazione*
    - *Conferimento*
    - *Campione*
    - *N. Parametri*
    - *Data Importazione*
    - *Stato Export* (badge colorato: Verde = Esportato, Arancione = Da esportare)
- **Pannello Detail (Parametri del Campione Selezionato)**:
  - Cliccando su una riga della tabella Master, il pannello inferiore/laterale mostra l'elenco dei parametri del campione:
    - *Parametro Strumento* (es. `Fluoruri`, `Cloruri`)
    - *Codice Esame LIS* (es. `BG00594`, `BG00590`)
    - *Valore Originale* (es. `n.a.`, `0,7733`)
    - *Valore Formattato per LIS* (es. `0`, `0,7733`)
    - *Stato Mappatura* (Valido / Non mappato)
- **Barra Inferiore Azioni**:
  - Riepilogo: *Totale campioni: X | Selezionati per export: Y | Già esportati: Z*.
  - Pulsante principale **"Esporta Selezionati per LIS"**.

### 9.3 Schermata Configurazione (Pannello Admin)
- **Tab 1 - Driver Strumento**: Selettore dropdown per impostare il driver predefinito dello strumento (es. Dionex IC, Spettrofotometro, ecc.) utilizzato nelle acquisizioni. Riservato all'Admin.
- **Tab 2 - Percorsi e Cartelle**: Configurazione dei percorsi di input (`sequenze/`), archivio (`archiviati/`), scarti (`errori/`) ed esportazione (`export/`).
- **Tab 3 - Tabella Transcodifiche**: Griglia per inserimento/modifica/eliminazione mappature parametri -> codici LIS, con pulsanti *Importa da file TXT* ed *Esporta su file TXT*.
- **Tab 4 - Gestione Utenti**: Tabella utenti con possibilità di creare nuovi account, assegnare ruoli (`Admin` / `Operatore`), resettare password ed eliminare account.
- **Tab 5 - Codici Laboratorio**: Gestione dei prefissi ammessi (es. `BG`, `MI`, `BS`, `RL`, `VP`, `MN`, `MB`).

---

## 10. SCHEMA DEL DATABASE (SQLITE)

Il database è strutturato con le seguenti tabelle relazionali:

### 10.1 `users`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `username`: TEXT UNIQUE NOT NULL
- `password_hash`: TEXT NOT NULL
- `salt`: TEXT NOT NULL
- `role`: TEXT NOT NULL CHECK(role IN ('ADMIN', 'OPERATORE'))
- `created_at`: DATETIME DEFAULT CURRENT_TIMESTAMP
- `last_login`: DATETIME

### 10.2 `configurations`
- `key`: TEXT PRIMARY KEY
- `value`: TEXT NOT NULL
- `description`: TEXT
- `updated_at`: DATETIME DEFAULT CURRENT_TIMESTAMP

### 10.3 `transcodings`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `instrument_param_name`: TEXT UNIQUE NOT NULL
- `lis_exam_code`: TEXT NOT NULL
- `lis_substance_code`: TEXT nullable; indice univoco `(lis_exam_code, lis_substance_code)` per regole attive con sostanza.
- `description`: TEXT
- `is_active`: INTEGER DEFAULT 1
- `updated_at`: DATETIME DEFAULT CURRENT_TIMESTAMP

### 10.4 `samples`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `sample_code`: TEXT UNIQUE NOT NULL (18 caratteri)
- `lab_code`: TEXT NOT NULL (2 caratteri)
- `year`: INTEGER NOT NULL (4 cifre es. 2026)
- `acceptance`: TEXT NOT NULL (es. 10442)
- `conferment`: INTEGER NOT NULL (es. 1)
- `sample_number`: INTEGER NOT NULL (es. 1)
- `source_filename`: TEXT NOT NULL
- `status`: TEXT NOT NULL DEFAULT 'DA_ESPORTARE' CHECK(status IN ('DA_ESPORTARE', 'ESPORTATO', 'ERRORE'))
- `imported_at`: DATETIME DEFAULT CURRENT_TIMESTAMP
- `exported_at`: DATETIME
- `export_filename`: TEXT

### 10.5 `sample_results`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `sample_id`: INTEGER NOT NULL REFERENCES samples(id) ON DELETE CASCADE
- `param_name`: TEXT NOT NULL
- `raw_value`: TEXT NOT NULL
- `numeric_value`: REAL
- `formatted_value`: TEXT NOT NULL
- `lis_exam_code`: TEXT
- `lis_substance_code`: TEXT nullable, snapshot della transcodifica all'importazione.
- `is_mapped`: INTEGER DEFAULT 1
- `is_exported`: INTEGER DEFAULT 0
- `exported_at`: DATETIME

Le colonne sostanza sono aggiunte con migrazione transazionale e ripetibile. I record precedenti rimangono senza sostanza; nessuna rimappatura o modifica degli stati di esportazione durante l'aggiornamento.

### 10.6 `audit_logs`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `user_id`: INTEGER REFERENCES users(id)
- `username`: TEXT NOT NULL
- `action`: TEXT NOT NULL (es. 'IMPORT_FILES', 'EXPORT_LIS', 'USER_CREATE', 'CONFIG_UPDATE')
- `details`: TEXT
- `timestamp`: DATETIME DEFAULT CURRENT_TIMESTAMP

---

## 11. STRUTTURA DEL PROGETTO

```text
strumenti/
├── AGENTS.md                   # Linee guida e regole operative dello sviluppo
├── PROJECT_CONTEXT.md          # Architettura e stato del progetto
├── SESSION_SUMMARY.md          # Diario delle sessioni di sviluppo
├── progetto.md                 # Specifiche complete del progetto (questo documento)
├── pyproject.toml              # Configurazione progetto e dipendenze uv
├── app.py                      # Entry point principale dell'applicazione
├── driver.py                   # Modulo isolato contenente tutti i driver degli strumenti
├── src/
│   ├── __init__.py
│   ├── database.py             # Connessione SQLite, schema DDL, migrazioni e repository
│   ├── auth.py                 # Gestione sicurezza, hashing password e sessioni utente
│   ├── config.py               # Gestione impostazioni applicative e percorsi
│   ├── exporter.py             # Generatore tracciato CSV per il LIS
│   ├── validator.py            # Validazione codice campione e integrità dati
│   └── gui/
│       ├── __init__.py
│       ├── app_window.py       # Finestra principale CustomTkinter
│       ├── login_view.py       # Vista di autenticazione
│       ├── master_detail.py    # Vista Master-Detail campioni e parametri
│       ├── settings_dialog.py  # Dialogo configurazioni (Admin)
│       └── components/         # Widget riutilizzabili (tabelle, badge, filtri)
├── data/                       # Directory contenente il database SQLite locale
├── sequenze/                   # Cartella di default per l'ingresso file strumenti
├── archiviati/                 # Cartella di default per i file elaborati con successo
├── errori/                     # Cartella di default per file con errori/anomalie
├── export/                     # Cartella di default per i file CSV esportati per il LIS
└── tests/                      # Suite di test unitari e di integrazione
```

---

## 12. PIANO DI VERIFICA E TESTING

1. **Test Unitari dei Driver (`driver.py`)**:
   - Parsing corretto dei file di esempio in `sequenze/` (`BG2600104420010001.txt`, `BG2600104430010001.txt`).
   - Gestione dei valori non numerici (`n.a.` -> `0`) e formattazione con virgola decimale.
2. **Test Validazione Codice Campione**:
   - Validazione codici corretti (18 caratteri con prefissi noti).
   - Rilevamento e scarto di codici non conformi.
3. **Test Database & Transcodifica**:
   - Inserimento campioni, parametri e transcodifiche.
   - Gestione sovrascrittura duplicati.
4. **Test di Esportazione CSV per LIS**:
   - Generazione file CSV e confronto byte-a-byte con il file di riferimento in `export/ESPORTAZIONE_20260831_102323.csv`.
5. **Test Interfaccia Grafica**:
   - Login con credenziali `admin`/`admin` e operatore.
   - Caricamento file, visualizzazione dettagli parametri, selezione ed esportazione.
   - Verifica permessi differenziati per le impostazioni.
