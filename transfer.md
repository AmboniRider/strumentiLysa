# Guida al Trasferimento e Installazione su un Nuovo PC (Senza Python)

Documentazione correlata del progetto:
- [manuale.md](file:///d:/pyprg/strumenti/manuale.md): Manuale operativo per l'operatore di laboratorio e l'amministratore.
- [README.md](file:///d:/pyprg/strumenti/README.md): Guida rapida al repository e comandi principali.
- [PROJECT_CONTEXT.md](file:///d:/pyprg/strumenti/PROJECT_CONTEXT.md): Architettura tecnica, stack tecnologico e convenzioni di sviluppo.
- [progetto.md](file:///d:/pyprg/strumenti/progetto.md): Specifiche funzionali e tracciato standard CSV a 24 colonne per il LIS.

Questa guida illustra la procedura passo-passo per trasferire ed eseguire l'applicazione **STRUMENTI ➔ LIS** su un nuovo computer con sistema operativo Windows **sprovvisto di ambiente Python**.

Grazie all'utilizzo di [`uv`](https://github.com/astral-sh/uv) (il package & project manager moderno per Python), **non è necessario installare manualmente Python**, né configurare le variabili d'ambiente di sistema (`PATH`). `uv` si occupa in autonomia di scaricare la versione corretta dell'interprete Python (>= 3.11), configurare l'ambiente virtuale dedicato e installare tutte le librerie necessarie in modo rapido, isolato e riproducibile.

---

## 1. Cartelle e File: Cosa Copiare e Cosa NON Copiare

Per trasferire il software tramite **chiavetta USB**, **cartella condivisa di rete** o **archivio compresso (.zip)**, fai riferimento a questa classificazione dettagliata.

> [!NOTE]
> Se la nuova postazione è connessa alla rete e dispone di Git con accesso al repository GitHub (`AmboniRider/strumentiLysa`), è preferibile clonare direttamente il repository con `git clone`. In questo caso, le esclusioni sono già gestite automaticamente dal file [.gitignore](file:///d:/pyprg/strumenti/.gitignore).

### 📋 Tabella Sinottica Rapida

| Percorso / File | Categoria | Stato | Note sintetiche |
| :--- | :--- | :---: | :--- |
| `src/` | Codice Sorgente | 🟢 **OBBLIGATORIO** | Core applicativo (GUI, database, modelli, servizi). |
| `app.py` | Entry Point | 🟢 **OBBLIGATORIO** | File principale di avvio con banner terminale ANSI. |
| `driver.py` | Driver Strumenti | 🟢 **OBBLIGATORIO** | Parser per Dionex IC, Mettler Toledo, Spettrofotometro. |
| `pyproject.toml` | Configurazione | 🟢 **OBBLIGATORIO** | Definizione dipendenze e metadati del progetto. |
| `uv.lock` | Dipendenze | 🟢 **OBBLIGATORIO** | Lockfile con versioni bloccate per riproducibilità esatta. |
| `strumenti.bat` | Script di Lancio | 🟢 **OBBLIGATORIO** | Avvio rapido con doppio clic su Windows. |
| `sync.bat` | Sincronizzazione | 🟡 **CONSIGLIATO** | Script batch per sync bidirezionale con GitHub. |
| `driver_implementati/` | Documentazione | 🟡 **CONSIGLIATO** | Schede tecniche e specifiche dei singoli driver. |
| `manuale.md`, `README.md`, `progetto.md` | Documentazione | 🟡 **CONSIGLIATO** | Manuale utente e specifiche funzionali. |
| `PROJECT_CONTEXT.md`, `SESSION_SUMMARY.md` | Documentazione | 🟡 **CONSIGLIATO** | Architettura tecnica e storico delle modifiche. |
| `agents.md`, `LICENSE` | Normative & Regole | 🟡 **CONSIGLIATO** | Linee guida di sviluppo e licenza software (GPL v3). |
| `.gitignore`, `.gitattributes` | Configurazione Git | 🟡 **CONSIGLIATO** | Gestione esclusioni e normalizzazione fine riga. |
| `tests/` | Suite di Test | 🟡 **CONSIGLIATO** | Indispensabile per il collaudo iniziale (`uv run pytest`). |
| `esempi/` | Tracciati di Esempio | 🟡 **CONSIGLIATO** | Dati campione per test senza usare dati di produzione. |
| `data/strumenti.db` | Database SQLite | 🟠 **OPZIONALE** | Copiare SOLO per migrare utenti/configurazioni già salvate. |
| `sequenze/`, `archiviati/`, `errori/`, `export/` | Cartelle di Lavoro | 🟠 **OPZIONALE** | Non serve copiarle: create in automatico vuote all'avvio. |
| `.venv/` o `venv/` | Ambiente Virtuale | 🔴 **NON COPIARE** | Percorsi assoluti e binari non portabili; ricreato con `uv sync`. |
| `__pycache__/`, `*.pyc` | Bytecode Python | 🔴 **NON COPIARE** | File intermedi ricompilati automaticamente da Python. |
| `.pytest_cache/`, `.pytest-*/` | Cache Test | 🔴 **NON COPIARE** | Dati temporanei delle precedenti esecuzioni di test. |
| `.uv-cache/`, `.ruff_cache/` | Cache Tool | 🔴 **NON COPIARE** | Cache temporanee locali degli strumenti di sviluppo. |
| `*.db-wal`, `*.db-shm` | Lock Database | 🔴 **NON COPIARE** | File transazionali temporanei SQLite: rischio corruzione. |
| File contenuti in `archiviati/` o `export/` | File Operativi | 🔴 **NON COPIARE** | Rischio di duplicazioni o re-invio campioni già processati al LIS. |
| File contenuti in `sequenze/` o `errori/` | File Operativi | 🔴 **NON COPIARE** | Evita di re-importare file analitici della postazione sorgente. |
| `.vscode/`, `.idea/`, `.codex/` | Configurazione IDE | 🔴 **NON COPIARE** | Preferenze personali dell'ambiente di sviluppo. |
| `.git-sandbox-backup/` | Backup Sandbox | 🔴 **NON COPIARE** | Cartella di backup temporanea della sandbox Git locale. |
| `.git/` | Repository Git | 🔴 **NON COPIARE** | In caso di trasferimento manuale USB/ZIP (usare `git clone` se serve Git). |
| `.env`, `.env.*`, `*.pem`, `*.key` | Segreti / Credenziali | 🔴 **NON COPIARE** | Credenziali e configurazioni riservate della postazione locale. |
| `Thumbs.db`, `Desktop.ini`, `*.log` | File di Sistema/Log | 🔴 **NON COPIARE** | File temporanei e di log generati da Windows o dai programmi. |

---

### ✅ 1.1 Nel Dettaglio: Cosa Copiare

#### 1. File Indispensabili per l'Esecuzione (Obbligatori)
- **`src/`**: La directory con l'intera architettura software:
  - `src/models.py`: Modelli dati condivisi (campioni, risultati, utenti).
  - `src/importer_service.py`: Logica di scansione, parsing, validazione e archiviazione file.
  - `src/database.py`: Gestione SQLite, schemi tabelle, indici e query.
  - `src/auth.py`: Autenticazione, hashing password (SHA-256 + salt) e gestione sessione/ruoli.
  - `src/config.py`: Gestione delle impostazioni applicative e percorsi cartelle.
  - `src/exporter.py`: Motore di generazione tracciato CSV per il LIS (24 colonne).
  - `src/validator.py`: Validatore codici campione a 18 caratteri.
  - `src/gui/`: Interfaccia grafica CustomTkinter (login, master-detail, impostazioni, guida contestuale).
- **`app.py`**: Entry point principale per avviare l'applicazione desktop, completo di terminal banner e impostazione titolo console.
- **`driver.py`**: Modulo con tutti i driver strumentali (`DionexICDriver`, `MettlerToledoDriver`, `SpectrophotometerDriver`).
- **`pyproject.toml`**: File di configurazione del progetto Python (specifica la versione Python `>=3.11`, le dipendenze `customtkinter`, `pillow` e gli strumenti di test).
- **`uv.lock`**: File di blocco deterministico delle dipendenze. Garantisce che `uv` installi sul nuovo PC le versioni esatte, identiche a quelle testate.
- **`strumenti.bat`**: Script di avvio rapido tramite doppio clic per Windows (configura codepage UTF-8, imposta il titolo della console e avvia l'app con `uv run`).

#### 2. Script e Strumenti di Sincronizzazione (Consigliati)
- **`sync.bat`**: Script batch che automatizza la sincronizzazione con il repository GitHub privato `AmboniRider/strumentiLysa` (esegue commit locale, fetch, merge e push preservando la storia). Include il flag `--check` per testare i prerequisiti.
- **`.gitignore`** e **`.gitattributes`**: Mantengono le regole di esclusione e la corretta gestione dei terminatori di riga Windows (CRLF).

#### 3. Documentazione Tecnica e Operativa (Consigliati)
- **`manuale.md`**: Manuale completo per gli operatori di laboratorio (workflow, unione duplicati, esportazione LIS e FAQ).
- **`README.md`**: Guida riassuntiva del progetto per sviluppatori e sistemisti.
- **`transfer.md`**: Questa guida di trasferimento.
- **`progetto.md`**: Specifiche complete dei requisiti e tracciato delle 24 colonne LIS.
- **`PROJECT_CONTEXT.md`** e **`SESSION_SUMMARY.md`**: Documenti di contesto architetturale e registro decisioni.
- **`agents.md`**: Linee guida e convenzioni per lo sviluppo.
- **`LICENSE`**: Testo della licenza GPL v3.
- **`driver_implementati/`**: Cartella contenente la documentazione approfondita dei singoli driver (`dionex_ic.md`, `mettler_toledo.md`, `spettrofotometro_uv_vis.md`, `README.md`).

#### 4. Suite di Collaudo ed Esempi (Consigliati)
- **`tests/`**: Suite completa di test automatizzati (`test_database.py`, `test_driver.py`, `test_duplicate_merge.py`, `test_exporter.py`, `test_gui.py`, `test_help.py`, `test_integration.py`, `test_mettler_integration.py`, `test_selective_export.py`, `test_validator.py`, `test_version_config.py`, `conftest.py`). Permette di collaudare l'integrità del sistema sul nuovo PC con il comando `uv run pytest`.
- **`esempi/`**: Cartella con tracciati strumentali di prova (`esempi/sequenze/`), simulazioni di export (`esempi/export/`) e file di mappatura (`mappatura_mettler.txt`, `esempio ESPORTAZIONE_solventi_sostanze.csv`).

#### 5. Dati Operativi: Come Gestire la Cartella `data/`
- **File `data/strumenti.db`**:
  - **Installazione Pulita (Consigliata per nuovi strumenti)**: **NON copiare** il file. All'avvio, l'applicazione creerà automaticamente un nuovo database SQLite con schema completo, regole di transcodifica predefinite e utente amministratore (`admin` / `admin`).
  - **Migrazione di Dati Esistenti**: Se si desidera trasferire anagrafiche utenti, personalizzazioni delle transcodifiche e storico campioni dal PC precedente:
    1. Assicurarsi che l'applicazione sul PC sorgente sia **completamente chiusa**.
    2. Copiare **solamente** il file `data/strumenti.db`.
    3. Non copiare mai i file `.db-wal` e `.db-shm`.

---

### ❌ 1.2 Nel Dettaglio: Cosa NON Copiare (Esclusioni Tassative)

| Elemento da Escludere | Perché NON Deve Essere Copiato (Motivazione Tecnica & Rischio) |
| :--- | :--- |
| **`.venv/` o `venv/`** | **CRITICO - MAI COPIARE**. L'ambiente virtuale contiene percorsi assoluti hardcoded verso la cartella del PC di origine, collegamenti simbolici/giunzioni NTFS e interpreti binari legati al sistema operativo di origine. Copiarlo genera errori di caricamento delle librerie o di permessi. Verrà ricreato in pochi secondi sul nuovo PC tramite `uv sync`. |
| **`__pycache__/` e `*.pyc`** | File binari bytecode compilati da Python (`.pyc`, `.pyo`, `.pyd`). Non sono necessari: Python li ricompila automaticamente al primo avvio in base all'hardware locale. |
| **`.pytest_cache/` e `.pytest-*/`** | Cartelle di cache e cartelle temporanee create durante l'esecuzione dei test (`.pytest-analysis-check`, `.pytest-analysis-tmp`, `.pytest-auth-review`, `.pytest-github-proof`, `.pytest-manual-check`). Inutili e pesanti. |
| **`.uv-cache/`, `.ruff_cache/`, `.mypy_cache/`** | Cache temporanee dei tool di sviluppo. Rallentano la copia e non servono all'applicazione. |
| **`*.db-wal` e `*.db-shm`** | File di journaling Write-Ahead Logging di SQLite generati quando il database è aperto o in transazione. Se copiati insieme al database, rischiano di corrompere i dati o impedire l'apertura del database sul nuovo computer. |
| **File in `sequenze/`** | **Rischio doppio inserimento**: se si copiano file di sequenza grezza dal vecchio PC nella cartella di input, il programma al primo avvio tenterà di re-importarli, generando duplicati o segnalazioni di conflitto. Le cartelle di lavoro devono partire vuote. |
| **File in `archiviati/`** | I file già archiviati sul vecchio PC non devono essere trasferiti (salvo esigenze di backup separato a lungo termine). Copiarli occuperebbe spazio inutile senza alcun beneficio per la nuova postazione. |
| **File in `errori/`** | Vecchi file scartati per anomalie sul vecchio PC; non devono essere replicati sul nuovo sistema. |
| **File in `export/`** | **Rischio critico per il LIS**: i file CSV generati in passato e già trasmessi al sistema informativo di laboratorio non devono essere presenti nella cartella di export del nuovo PC, per evitare il rischio che un operatore li trasmetta una seconda volta. |
| **`.vscode/`, `.idea/`, `.codex/`, `.agents/`** | Configurazioni personali dell'editor o degli agenti di sviluppo. |
| **`.git-sandbox-backup/`** | Backup temporanei interni di Git. |
| **`.git/`** | Se il trasferimento avviene tramite supporto fisico (chiavetta USB o ZIP), omettere la cartella `.git` per mantenere il pacchetto leggero e pulito. (Se si usa Git sul nuovo PC, eseguire invece `git clone`). |
| **`.env`, `.env.*`, `*.pem`, `*.key`** | Eventuali file di variabili d'ambiente locali, chiavi crittografiche o certificati personali. |
| **`Thumbs.db`, `Desktop.ini`, `*.log`** | File nascosti generati da Windows Explorer o file di log residui. |

---

## 2. Procedura Passo-Passo sul Nuovo PC

Segui questi passaggi sul nuovo computer (sul quale non è presente Python):

### Passo 1: Posizionare i file del software

1. Crea o scegli una cartella di destinazione sul nuovo PC (ad esempio `C:\LabSoftware\strumenti` o `D:\strumenti`).
2. Copia all'interno di questa cartella tutti i file e le cartelle indicati nella sezione **DA COPIARE**.
   *(In alternativa, se la macchina è connessa a Internet e dispone di Git: `git clone https://github.com/AmboniRider/strumentiLysa.git C:\LabSoftware\strumenti`).*

---

### Passo 2: Installare `uv` tramite PowerShell

1. Apri **PowerShell** sul nuovo PC (puoi cercarlo nel menu Start di Windows o premere `Win + R`, digitare `powershell` e premere Invio).
2. Esegui il comando ufficiale di installazione:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

> [!NOTE]
> Se la sessione PowerShell è già abilitata all'esecuzione di script, puoi utilizzare la forma breve:
> ```powershell
> irm https://astral.sh/uv/install.ps1 | iex
> ```

3. **Chiudi e riapri PowerShell** (oppure riavvia la sessione terminale) per consentire a Windows di ricaricare la variabile d'ambiente `PATH`.
4. Verifica che `uv` sia raggiungibile digitando:
   ```powershell
   uv --version
   ```
   Dovresti visualizzare la versione di `uv` installata (es. `uv 0.6.x` o superiore).

---

### Passo 3: Creare l'ambiente ed eseguire il sync iniziale

1. In PowerShell, spostati nella cartella in cui hai copiato il software:
   ```powershell
   cd C:\LabSoftware\strumenti
   ```
   *(Sostituisci il percorso con quello effettivo sul tuo computer).*

2. Esegui il comando di sincronizzazione:
   ```powershell
   uv sync
   ```

**Cosa fa questo comando automaticamente:**
- Rileva che sul computer non è presente Python (o che manca la versione richiesta `>=3.11`).
- Scarica in modo totalmente trasparente l'interprete Python autonomo ufficiale per Windows a 64 bit (senza toccare il registro di Windows né i programmi di sistema).
- Crea la cartella dell'ambiente virtuale isolato `.venv`.
- Installa tutte le librerie necessarie (`customtkinter`, `pillow`, `pytest`, ecc.) alle versioni esatte bloccate in `uv.lock`.

---

### Passo 4: Verifica dell'Integrità (Test Automatici)

Prima di avviare l'interfaccia operativa, è vivamente consigliato eseguire la suite completa di test inclusa per certificare che tutti i moduli (validatore, database, driver Dionex/Mettler/Spettrofotometro, merge duplicati, exporter LIS e interfaccia grafica) funzionino perfettamente sull'hardware del nuovo PC:

```powershell
uv run pytest
```

Tutti i test (45 test) dovranno risultare superati con esito positivo:
```text
============================= 45 passed in X.XXs ==============================
```

---

### Passo 5: Avvio dell'Applicazione

Puoi avviare il programma in due modalità:

#### Modalità Rapida (Doppio Clic)
Fai doppio clic sul file batch:
```text
strumenti.bat
```
Lo script imposta la codifica UTF-8 per il terminale, apre la console con il titolo dedicato (`STRUMENTI -> LIS - ACQUISIZIONE DATI`), mostra il banner colorato e avvia l'interfaccia grafica.

#### Modalità da Terminale
Da PowerShell o Prompt dei comandi, posizionati nella cartella del programma ed esegui:
```powershell
uv run python app.py
```

---

## 3. Credenziali di Primo Accesso

Se hai scelto di **non copiare** il database `data/strumenti.db` (installazione pulita) o se viene generato per la prima volta:
- **Nome Utente**: `admin`
- **Password predefinita**: `admin`
- **Ruolo**: `ADMIN`

> [!IMPORTANT]
> Al primo accesso, si consiglia vivamente di cambiare la password dell'amministratore tramite il pulsante **🔑 Password** nella barra superiore e di creare le utenze dedicate agli operatori nella scheda **⚙️ Impostazioni ➔ 👥 Gestione Utenti**.

---

## 4. Scenario Particolare: PC di Laboratorio Offline (Senza Connessione Internet)

Se il PC di laboratorio collegato allo strumento è isolato e **privo di accesso a Internet**:

1. **Installazione di `uv` offline**:
   - Scarica l'archivio ZIP standalone di `uv` per Windows x86_64 da un PC connesso tramite la pagina GitHub Releases: `https://github.com/astral-sh/uv/releases/latest` (es. `uv-x86_64-pc-windows-msvc.zip`).
   - Estrai l'eseguibile `uv.exe` e posizionalo direttamente nella cartella del software sul PC di destinazione (o in una cartella presente nel `PATH`).

2. **Preparazione con cache o Python portabile**:
   - Sul PC connesso con la stessa versione di Windows, esegui:
     ```powershell
     uv sync
     ```
   - Individua la cartella dell'interprete Python autonomo scaricato da `uv` (solitamente in `%LOCALAPPDATA%\uv\python\`) e la cartella cache (`uv cache dir`).
   - Copia la cartella dell'interprete Python sul PC offline nel percorso corrispondente `%LOCALAPPDATA%\uv\python\` (oppure posiziona l'interprete e indica a `uv` il percorso tramite la variabile `UV_PYTHON`).
   - Una volta presente l'interprete e sincronizzata la cartella `.venv` con percorsi rilocabili, `uv run python app.py` funzionerà al 100% in modalità offline senza richiedere alcuna connessione esterna.

---

## 5. Riepilogo Comandi Rapidi (Cheat-Sheet)

```powershell
# 1. Installazione uv (da PowerShell sul nuovo PC connesso)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Spostarsi nella cartella del programma
cd C:\Percorso\Della\Cartella\strumenti

# 3. Creazione automatica ambiente virtuale e download dipendenze
uv sync

# 4. Esecuzione suite completa di collaudo (45 test)
uv run pytest

# 5. Avvio applicazione
uv run python app.py
# (oppure doppio clic sul file strumenti.bat)

# 6. (Opzionale) Verifica stato Git / Sincronizzazione GitHub
sync.bat --check
sync.bat
```
