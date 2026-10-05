# strumentiLysa

Applicazione desktop locale per acquisire file di strumenti di laboratorio,
gestire campioni e risultati su SQLite ed esportare CSV per il LIS.
Supporta Dionex IC, Mettler Toledo e UV-Vis tramite driver dedicati.

## Installazione e avvio

Prerequisiti: Git, `uv` e accesso al repository privato su GitHub.

```powershell
git clone https://github.com/AmboniRider/strumentiLysa.git
cd strumentiLysa
uv sync --locked
uv run python app.py
```

Su Windows è disponibile anche `strumenti.bat` per l'avvio con doppio clic.
Le cartelle operative vengono create quando necessarie; su un'installazione nuova
il database viene inizializzato dall'applicazione. Utenti, impostazioni e dati
delle altre postazioni non vengono trasferiti attraverso Git.

## Sincronizzazione

Dalla cartella del progetto eseguire:

```powershell
.\sync.bat
```

Il comando registra automaticamente tutte le modifiche non escluse da `.gitignore`
(incluse le rimozioni), scarica gli aggiornamenti, integra il ramo remoto con un
merge e carica i commit su GitHub. Richiede una configurazione Git valida per
nome/email e l'autenticazione GitHub tramite Git Credential Manager o il metodo
già configurato su quella postazione. Non memorizza password o token nello script.

In caso di conflitti si interrompe: controllare `git status`, risolvere i file,
registrare la risoluzione con `git add` e `git commit`, quindi ripetere il comando.
Se il caricamento viene rifiutato perché un'altra postazione ha pubblicato nel
frattempo, ripetere la sincronizzazione. Non vengono usati push forzati.

Per verificare i prerequisiti senza modificare il repository o accedere alla rete:

```powershell
.\sync.bat --check
```

Sono esclusi `.venv`, cache, file temporanei, credenziali, database e contenuti delle
cartelle operative `data`, `sequenze`, `archiviati`, `errori`, `export`.
La cartella `esempi` contiene invece i tracciati di riferimento utilizzati dai test.
La sincronizzazione riguarda il progetto; per salvare i dati operativi usare una
procedura di backup separata.

## Verifica e documentazione

```powershell
uv run pytest
```

- [Manuale operatore](manuale.md)
- [Specifiche](progetto.md)
- [Architettura e TODO](PROJECT_CONTEXT.md)
- [Installazione su altre postazioni](transfer.md)
- [Driver implementati](driver_implementati/README.md)

Licenza: AGPL-3.0-or-later, vedere [LICENSE](LICENSE).
