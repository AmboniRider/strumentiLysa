# Aggiornamenti e copie del database

## Uso sulla postazione installata

All'avvio il programma controlla le Release stabili pubbliche di
`AmboniRider/strumentiLysa`, in background, con timeout di rete di 10 secondi.
Internet non è richiesto per lavorare. Una nuova versione genera un solo popup
per avvio per tutti gli utenti; gli operatori devono rivolgersi all'amministratore.
Un errore di connessione non interrompe il lavoro ed è visibile nel pannello.

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
- `transcodifiche.txt`: canali già codificati nel formato `Parametro:Esame[:Sostanza]`;
- `previous/` e `previous-env/`: programma e ambiente precedenti;
- `result.txt`: esito e indicazioni diagnostiche.

Il dialogo ricorda di esportare i canali e indica la cartella. Il recupero delle
transcodifiche è automatico; il TXT è disponibile anche per l'importazione manuale
da **Impostazioni → Transcodifiche LIS → Importa TXT**. Il TXT non include le
descrizioni e gli stati di attivazione: questi sono conservati dal recupero completo.

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
copia dei soli file del pacchetto `strumenti-update-2.0.1.zip` nell'installazione.
Eseguire nuovamente `installa.bat` per allineare le dipendenze. Conservare
`data/strumenti.db` e tutte le cartelle operative. Lo ZIP include il nuovo
`strumenti.bat` per abilitare il recupero da Python base.
Non usare lo ZIP di trasferimento con database ripulito per sovrascrivere
una postazione esistente. La 2.0.0 migra lo schema storico 0 allo schema 1 senza
perdita di dati.

## Preparazione di una Release

1. Allineare `src.__version__`, `pyproject.toml` e `uv.lock`. Modificare
   `DATABASE_SCHEMA_VERSION` solo con una migrazione consecutiva esplicita.
2. Aggiornare `RELEASE_NOTES.md` e la politica nella chiamata a `build_release.py`
   nel workflow. La politica predefinita 2.0.1 è `migrate`, schema sorgente 0–1,
   schema destinazione 1. Per `reset` specificare sempre `--losses`.
3. Eseguire `uv run python -m pytest -q` e, su Windows, il collaudo completo:

   ```powershell
   $env:STRUMENTI_UPDATE_E2E = '1'
   uv run python -m pytest tests/test_update_installation.py -q
   ```

4. Generare con `uv run python build_release.py --output dist/release`.
   I file non vengono sovrascritti: usare una cartella nuova per una seconda build.
5. Creare e inviare un tag stabile come `v2.0.0`. Il workflow Windows verifica
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
