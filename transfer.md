# Guida al Trasferimento e Installazione su un Nuovo PC (Senza Python)

Vedi il file completo [transer.md](file:///d:/pyprg/strumenti/transer.md).

Questa guida illustra la procedura passo-passo per copiare ed eseguire l'applicazione **STRUMENTI ➔ LIS** su un nuovo computer con sistema operativo Windows **sprovvisto di ambiente Python**.

Grazie all'utilizzo di [`uv`](https://github.com/astral-sh/uv) (il package & project manager moderno per Python), **non è necessario installare manualmente Python**, né configurare le variabili d'ambiente di sistema (`PATH`). `uv` si occupa in autonomia di scaricare la versione corretta dell'interprete Python, configurare l'ambiente virtuale dedicato e installare tutte le dipendenze necessarie in modo rapido, isolato e riproducibile.

---

## 1. Cartelle e File: Cosa Copiare e Cosa NON Copiare

Per trasferire il software (tramite chiavetta USB, cartella condivisa di rete o archivio `.zip`), seleziona i file e le cartelle secondo lo schema seguente:

### ✅ DA COPIARE (Necessari)

| Percorso / File | Descrizione |
| :--- | :--- |
| `src/` | **Obbligatorio**. Intero codice sorgente dell'applicazione (logica, interfaccia grafica CustomTkinter, validatori, servizi). |
| `app.py` | **Obbligatorio**. File di avvio principale dell'applicazione con banner e gestione terminale. |
| `driver.py` | **Obbligatorio**. Driver isolati per l'acquisizione dei file degli strumenti di laboratorio. |
| `pyproject.toml` | **Obbligatorio**. Configurazione del progetto, requisiti di versione Python e librerie dipendenti. |
| `uv.lock` | **Obbligatorio**. File di blocco delle dipendenze: garantisce l'installazione delle versioni esatte e testate. |
| `strumenti.bat` | **Obbligatorio**. Script batch per l'avvio rapido dell'applicazione con doppio clic. |
| `esempi/` | **Consigliato**. File di test, tracciati di esempio e sequenze analitiche utili per verifiche iniziali. |
| `tests/` | **Consigliato**. Suite completa di test unitari e di integrazione per verificare la corretta installazione. |
| `data/` | **Opzionale**. Contiene il database SQLite locale `strumenti.db`. Copialo se vuoi trasferire utenti, impostazioni e regole di transcodifica già configurate. *Se non lo copi, l'applicazione creerà automaticamente un nuovo database con configurazioni di default e utente `admin` / `admin`.* |
| `sequenze/` | **Opzionale**. Cartella di input per i file generati dagli strumenti. Se omessa, verrà creata automaticamente all'avvio. |
| `archiviati/` | **Opzionale**. Cartella archivio file elaborati. Creata automaticamente se non presente. |
| `errori/` | **Opzionale**. Cartella file scartati/non conformi. Creata automaticamente se non presente. |
| `export/` | **Opzionale**. Cartella di destinazione dei file CSV per il LIS. Creata automaticamente se non presente. |
| `progetto.md`, `PROJECT_CONTEXT.md` | **Consigliato**. Documentazione tecnica delle specifiche e dell'architettura del software. |

---

### ❌ DA NON COPIARE (Da escludere tassativamente)

| Percorso / File | Motivo dell'esclusione |
| :--- | :--- |
| `.venv/` | **NON copiare mai**. L'ambiente virtuale contiene percorsi assoluti, binari compilati e script legati in modo univoco al computer di origine. Verrà rigenerato automaticamente sul nuovo PC con `uv sync`. |
| `__pycache__/` (e sottocartelle) | **NON copiare**. File bytecode compilati temporanei (`.pyc`). Python li ricompila automaticamente all'avvio sul nuovo PC. |
| `.pytest_cache/` | **NON copiare**. File di cache temporanea generati durante l'esecuzione dei test sul PC di sviluppo. |
| `*.db-wal`, `*.db-shm` | **NON copiare**. File temporanei del database SQLite attivi quando il database è aperto. Se copi la cartella `data/`, assicurati che l'applicazione sul PC di origine sia **completamente chiusa** e copia solo il file `data/strumenti.db`. |

---

## 2. Procedura Passo-Passo sul Nuovo PC

Segui questi passaggi sul nuovo computer (sul quale non è presente Python):

### Passo 1: Posizionare i file del software

1. Crea o scegli una cartella di destinazione sul nuovo PC (ad esempio `C:\LabSoftware\strumenti` o `D:\strumenti`).
2. Copia all'interno di questa cartella tutti i file e le cartelle indicati nella sezione **DA COPIARE**.

---

### Passo 2: Installare `uv` tramite PowerShell

1. Apri **PowerShell** sul nuovo PC (puoi cercarlo nel menu Start di Windows o premere `Win + R`, digitare `powershell` e premere Invio).
2. Esegui il seguente comando ufficiale di installazione:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

> [!NOTE]
> Se la sessione PowerShell è già configurata per l'esecuzione di script, puoi utilizzare la forma abbreviata:
> ```powershell
> irm https://astral.sh/uv/install.ps1 | iex
> ```

3. **Chiudi e riapri PowerShell** (oppure riavvia il terminale) per consentire a Windows di ricaricare la variabile d'ambiente `PATH`.
4. Verifica che `uv` sia installato correttamente digitando:
   ```powershell
   uv --version
   ```
   Dovresti visualizzare l'output con la versione di `uv` installata (es. `uv 0.x.x`).

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
- Scarica in modo totalmente trasparente l'interprete Python autonomo ufficiale (senza toccare il registro di Windows né i programmi di sistema).
- Crea la cartella dell'ambiente virtuale isolato `.venv`.
- Installa tutte le librerie necessarie (`customtkinter`, `pillow`, `pytest`, ecc.) alle versioni esatte bloccate in `uv.lock`.

---

### Passo 4: Verifica dell'Integrità (Test Automatici)

Prima di avviare l'interfaccia operativa, è consigliabile eseguire la suite di test inclusa per certificare che tutti i moduli (validatore, database, driver, exporter, interfaccia) funzionino perfettamente sull'hardware del nuovo PC:

```powershell
uv run pytest
```

Tutti i test (18 test) dovranno risultare superati con esito positivo (`18 passed`).

---

### Passo 5: Avvio dell'Applicazione

Puoi avviare il programma in due modi:

#### Modalità Rapida (Doppio Clic)
Fai doppio clic sul file batch:
```text
strumenti.bat
```
Lo script imposta la codifica corretta per il terminale, apre la console con il titolo dedicato e avvia l'interfaccia grafica.

#### Modalità da Terminale
Da PowerShell o Prompt dei comandi, posizionati nella cartella ed esegui:
```powershell
uv run python app.py
```

---

## 3. Credenziali di Primo Accesso

Se hai scelto di **non copiare** il database `data/strumenti.db` (o se viene generato per la prima volta):
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
   - Estrai l'eseguibile `uv.exe` e posizionalo in una cartella a scelta o direttamente nella cartella del software sul PC di destinazione.

2. **Preparazione ambiente con cache portabile**:
   - Sul PC connesso, esegui:
     ```powershell
     uv cache dir
     ```
   - Puoi copiare sia la cartella `.venv` generata sul PC di sviluppo (purché entrambi i PC abbiano la stessa architettura Windows a 64 bit e il percorso di installazione sia identico o gestito con virtualenv rilocabile), oppure copiare la cartella cache di `uv` e la cartella Python di uv (`%LOCALAPPDATA%\uv\python\`) sul PC di destinazione.
   - Una volta copiate, eseguire `uv run python app.py` non richiederà alcuna connessione internet.

---

## 5. Riepilogo Comandi Rapidi (Cheat-Sheet)

```powershell
# 1. Installazione uv (da PowerShell sul nuovo PC)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# 2. Spostarsi nella cartella del programma
cd C:\Percorso\Della\Cartella\strumenti

# 3. Creazione automatica ambiente e download dipendenze
uv sync

# 4. Esecuzione test di collaudo
uv run pytest

# 5. Avvio applicazione
uv run python app.py
# (oppure doppio clic su strumenti.bat)
```
