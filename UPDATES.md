# Aggiornamenti e copie del database

## Uso sulla postazione installata

La **2.1.0** aggiunge Agilent 6460 LCMS, gestione dei risultati non mappati e
descrizioni nel TXT delle transcodifiche. Lo schema resta 1. Al primo avvio,
i campioni con tutti i risultati mappati già inviati e solo ignoti rimanenti
passano a Esportato; gli ignoti non vengono marcati inviati. I campioni con
soli ignoti restano Da esportare. Il riallineamento è registrato nell'audit.

All'avvio il programma controlla le Release stabili pubbliche di
`AmboniRider/strumentiLysa`, in background. Il controllo dei metadati ha un budget
di 10 secondi per richiesta; il download dello ZIP ha un budget totale di 5 minuti,
con timeout di inattività sul socket di 10 secondi.
Internet non è richiesto per lavorare. Una nuova versione genera un solo popup
per avvio per tutti gli utenti; gli operatori devono rivolgersi all'amministratore.
Un errore di connessione non interrompe il lavoro ed è visibile nel pannello.

Dalla 2.0.2, su Windows il downloader usa `truststore` e la verifica nativa
CryptoAPI, mantenendo attivi i controlli su certificati e hostname. Questo
permette la gestione nativa della catena e degli intermedi mancanti. Gli errori
di certificato, HTTP e timeout sono distinti nel pannello e il controllo fallito
viene segnalato anche in console. Se l'ambiente non contiene la nuova dipendenza,
eseguire `installa.bat` sulla postazione distribuita o `uv sync --locked` sul clone.

Con un utente **ADMIN** aprire **Impostazioni → Aggiornamenti e backup**:

- **Verifica aggiornamenti** consulta nuovamente GitHub e mostra le note.
- **Installa e riavvia** verifica compatibilità, spazio, SHA-256 e tutti i file
  del pacchetto. Dopo conferma chiude il programma e usa un processo esterno.
- **Crea copia database** salva una copia completa datata nella cartella scelta.
  Non sovrascrive copie esistenti e verifica integrità e chiavi esterne. La copia
  include utenti/password sotto forma di hash, impostazioni, transcodifiche,
  campioni, risultati e audit. Non contiene i file strumentali nelle cartelle esterne.

Le copie restano sul PC; nessun database viene inviato a GitHub.
Custodire le copie in una destinazione appropriata: contengono tutti i dati locali.
È ammessa una sola istanza del programma per cartella di installazione.

## Effetti sul database

Prima dell'installazione sono mostrate queste condizioni:

| Condizione | Effetto |
| --- | --- |
| Database conservato | Nessuna sostituzione o modifica dello schema |
| Migrazione senza perdita | Schema aggiornato su una copia, conservando i dati |
| Database nuovo | Perdita di campioni, risultati e audit, con conferma dedicata |

Per un database nuovo, il programma crea il file localmente: non scarica database
operativi da GitHub. Recupera utenti con password e ruoli, impostazioni e tutte
le transcodifiche compatibili, incluse descrizioni e stati di attivazione.
Se il recupero non riesce, interrompe l'aggiornamento e mantiene la versione precedente.

Prima di cambiare file il processo salva sempre in `.updates/<identificativo>/`:

- `database.db`: backup completo precedente;
- `transcodifiche.txt`: canali nel formato storico `Parametro:Esame[:Sostanza]`;
- `previous/` e `previous-env/`: programma e ambiente precedenti;
- `result.txt`: esito e indicazioni diagnostiche.

Il dialogo ricorda di esportare i canali e indica la cartella. Il recupero delle
transcodifiche è automatico; il TXT è disponibile anche per l'importazione manuale
da **Impostazioni → Transcodifiche LIS → Importa TXT**. Il TXT automatico del
runner mantiene il formato storico senza descrizioni; descrizioni e stati di
attivazione sono conservati dal recupero completo del database. Dalla 2.1.0,
l'export manuale dalla scheda Transcodifiche LIS include invece quattro campi:
`Parametro:Esame:Sostanza:Descrizione`, con sostanza vuota per gli standard.
Restano importabili i vecchi file a due/tre campi, preservando le descrizioni
già configurate se il file non le specifica.

Non cancellare `.updates` durante un aggiornamento. Non è prevista cancellazione
automatica dei backup. Dopo un errore viene ripristinata l'installazione precedente.
Dopo un arresto improvviso il lanciatore tenta il recupero usando Python base,
anche se l'ambiente virtuale è incompleto, prima di aprire l'app e il database.
Se il recupero fallisce, l'avvio resta bloccato: conservare `.updates` per assistenza.
La funzione di ripristino manuale dei backup non è inclusa nel pannello.

## Requisiti e prima adozione

L'installazione automatica è destinata ai pacchetti Windows x64 creati da
`transfer.bat`, con `.tools/uv.exe`, runtime e ambiente virtuale locali.
Per installare aggiornamenti e dipendenze serve Internet; l'uso successivo resta offline.
Le copie di sviluppo con `.git` permettono controlli e backup ma usano il flusso
Git per aggiornare il codice, conservando le modifiche locali.

La versione mostrata deriva da `src.__version__`, è in sola lettura e non dipende
dal vecchio valore `app_version` nel database.

Le installazioni prive dell'updater richiedono un aggiornamento manuale iniziale,
ad applicazione chiusa, con backup completo e
copia dei soli file del pacchetto `strumenti-update-2.1.0.zip` nell'installazione.
Eseguire nuovamente `installa.bat` per allineare le dipendenze. Conservare
`data/strumenti.db` e tutte le cartelle operative. Lo ZIP include il nuovo
`strumenti.bat` per abilitare il recupero da Python base.
Non usare lo ZIP di trasferimento con database ripulito per sovrascrivere
una postazione esistente. La 2.0.0 migra lo schema storico 0 allo schema 1 senza
perdita di dati.

## Aggiornamento manuale tramite Git

Questa alternativa è disponibile quando la verifica o il download dall'updater
falliscono, anche per problemi di certificati HTTPS in Python. Richiede **Git
installato** e una connessione funzionante dal client Git. Se anche Git segnala
errori TLS, risolvere la fiducia dei certificati senza disattivare la verifica SSL.
`main` contiene il codice corrente; consultare le note della versione prima
di applicarlo a una postazione operativa.

Prima creare una **copia completa del database** dal pannello e conservare i
file strumentali necessari, poi chiudere l'applicazione. Il trasferimento del
codice mantiene il database locale; al successivo avvio possono essere applicate
le migrazioni previste dalla versione. La procedura manuale **non attiva il
backup e il rollback automatici** del runner.

### Cartella che contiene già `.git`

Servono Git e uv. Aprire PowerShell nella cartella del programma. Eseguire
ogni comando separatamente e fermarsi al primo errore:

```powershell
git status --short
git ls-files data '*.db' '*.db-wal' '*.db-shm'
```

Se ci sono modifiche ai file versionati, conservarle e risolverle prima di
proseguire. Il secondo comando non deve elencare il database: il repository
ufficiale esclude `data/`, `*.db`, `*.db-wal` e `*.db-shm`. In una copia
personalizzata con database già versionato, fermarsi e far verificare la
configurazione; aggiungerlo a `.gitignore` non basta a smettere di tracciarlo.

Con copia di lavoro pulita e database non tracciato:

```powershell
git switch main
git pull --ff-only origin main
uv sync --locked --no-dev --no-install-project
.\strumenti.bat
```

`--ff-only` interrompe l'aggiornamento se i rami divergono. Fermarsi anche in
caso di conflitti o modifiche locali: non forzare la sostituzione dei file.
Questi comandi scaricano il codice senza commit o push automatici. `sync.bat`
rimane la procedura di sincronizzazione bidirezionale per chi sviluppa e vuole
anche pubblicare le proprie modifiche.

### Installazione da pacchetto senza `.git`

La cartella installata contiene `.tools/uv.exe`, `.venv` e `installa.bat`, ma
non è un repository. Aprire PowerShell nella cartella operativa, per esempio
`C:\strumenti`, e usare **una nuova cartella sorgenti separata**. Non copiare
direttamente tutto il clone: il suo `strumenti.bat` è quello di sviluppo.

Negli esempi la cartella sorgenti è `..\strumenti-sorgenti`; se esiste già,
scegliere un altro nome e sostituirlo in tutti i percorsi. Eseguire i comandi
uno alla volta, fermandosi se falliscono:

```powershell
git clone --branch main --single-branch https://github.com/AmboniRider/strumentiLysa.git ..\strumenti-sorgenti
```

Generare il pacchetto con il Python già installato. Il generatore usa solo la
libreria standard, legge i sorgenti del clone e include il launcher corretto:

```powershell
.\.venv\Scripts\python.exe ..\strumenti-sorgenti\build_release.py --output ..\strumenti-sorgenti\dist\aggiornamento-git
```

La generazione deve terminare correttamente. Aprire
`..\strumenti-sorgenti\dist\aggiornamento-git` ed estrarre il solo
`strumenti-update-<versione>.zip` nella cartella operativa, confermando la
sostituzione dei file del programma. Lo ZIP segue una whitelist di sorgenti,
documenti e launcher: **non contiene database né cartelle operative**.

Conservare `data/strumenti.db`, eventuali `strumenti.db-wal` e
`strumenti.db-shm`, le cartelle operative e le directory locali `.tools`,
`.runtime`, `.venv` e `.updates`. Usare poi l'installer già presente per
riallineare le dipendenze al nuovo `uv.lock`, quindi avviare:

```powershell
.\installa.bat
.\strumenti.bat
```

Se l'installer fallisce, fermarsi e non avviare l'applicazione finché il
problema non è risolto. Questa procedura non converte la cartella operativa
in un repository; gli aggiornamenti Git successivi richiedono nuovamente
una copia sorgenti e un nuovo pacchetto. **Non usare lo ZIP di trasferimento**,
che contiene un database ripulito destinato alle nuove installazioni.

Riferimenti Git: [pull e fast-forward](https://git-scm.com/docs/git-pull),
[file ignorati e già tracciati](https://git-scm.com/docs/gitignore).

## Preparazione di una Release

1. Allineare `src.__version__`, `pyproject.toml` e `uv.lock`. Modificare
   `DATABASE_SCHEMA_VERSION` solo con una migrazione consecutiva esplicita.
2. Aggiornare `RELEASE_NOTES.md` e la politica nella chiamata a `build_release.py`
   nel workflow. La politica predefinita 2.0.2 è `migrate`, schema sorgente 0–1,
   schema destinazione 1. Per `reset` specificare sempre `--losses`.
3. Eseguire `uv run python -m pytest -q` e, su Windows, il collaudo completo:

   ```powershell
   $env:STRUMENTI_UPDATE_E2E = '1'
   uv run python -m pytest tests/test_update_installation.py -q
   ```

4. Generare con `uv run python build_release.py --output dist/release`.
   I file non vengono sovrascritti: usare una cartella nuova per una seconda build.
5. Creare e inviare un tag stabile come `v2.0.2`. Il workflow Windows verifica
   tag, test e pacchetto, poi pubblica la **Release stabile** con ZIP e manifest.
   Il push di un tag stabile autorizza la pubblicazione; il normale push su
   `main` non pubblica Release. Verificare note e pacchetto prima di inviare il tag.

Il manifest `update-manifest.json`, formato 1, contiene:

- versione e intervallo Python (`min`, `max_exclusive`);
- politica database (`mode`, `min_schema`, `max_schema`, `target_schema`, `losses`);
- URL del pacchetto sotto le Release del repository e SHA-256;
- mappa dei soli file runtime gestiti e relativo SHA-256.

Il runtime rifiuta manifest mancanti/incompatibili, file extra, percorsi traversali,
archivi alterati, schema futuro e sostituzioni non confermate. Le Release non
contengono database, test, Git, backup o file operativi. Il formato non usa
credenziali o token sui PC installati: l'origine è GitHub pubblico tramite HTTPS.

Riferimenti: [GitHub Releases](https://docs.github.com/en/rest/releases/releases),
[asset delle Release](https://docs.github.com/en/rest/releases/assets),
[SQLite Online Backup API](https://www.sqlite.org/backup.html).
