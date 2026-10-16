# Trasferimento e installazione di Strumenti-LIS

Questa procedura prepara una nuova postazione **Windows x64** senza Python,
uv o Git preinstallati. Serve Internet per installare o ripristinare l'ambiente;
dopo l'installazione l'applicazione funziona offline.

## 1. Creare il pacchetto sulla postazione attuale

1. È consigliabile chiudere Strumenti-LIS per trasferire le configurazioni definitive.
2. Fare doppio clic su `transfer.bat`, oppure eseguire `uv run --locked python trasfer.py`.
3. Premere **Sfoglia...** e scegliere la cartella in cui salvare lo ZIP
   (anche una chiavetta USB o una cartella condivisa).
4. Premere **Crea ZIP** e attendere il messaggio di completamento.
5. Trasferire il solo file `strumenti_transfer_<data_ora>.zip` sul nuovo PC.

La cartella scelta è quella che riceve lo ZIP, non il percorso definitivo sul nuovo PC.
Il programma richiede il database `data/strumenti.db` e tutti i file applicativi.
Non sovrascrive archivi esistenti e non modifica i dati della postazione sorgente.

## 2. Contenuto del pacchetto

Lo ZIP contiene una sola cartella `strumenti` con:

- `app.py`, `driver.py` e i moduli Python di `src/`;
- `pyproject.toml` e `uv.lock`, per installare le dipendenze nelle versioni bloccate;
- `manuale.md`, `progetto.md`, `driver_implementati/`, `transfer.md` e `LICENSE`;
- `data/strumenti.db`, copia ripulita del database;
- `installa.bat` e `strumenti.bat`, dedicati alla nuova postazione.

| Informazioni del database | Trasferimento |
| --- | --- |
| Utenti, ruoli e credenziali applicative memorizzate | Conservati: usare gli account esistenti |
| Transcodifiche e impostazioni, inclusa la versione visualizzata | Conservate |
| Percorsi di input, archivio, errori ed export | Ricreati sotto la nuova cartella |
| Campioni, risultati, storico e stati di esportazione | Esclusi |
| Tutti i log di audit | Esclusi |

Le tabelle operative restano presenti ma vuote, con contatori ripristinati.
La copia usa SQLite Backup API anche in presenza di transazioni confermate nel WAL;
le cancellazioni e `VACUUM` avvengono soltanto nella copia temporanea.

Sono esclusi file strumentali, CSV esportati, Git, sincronizzazione GitHub, test,
esempi, cache, ambienti virtuali, log, configurazioni IDE e documentazione di sviluppo.
Il generatore di trasferimento resta sulla postazione di sviluppo.

Lo ZIP contiene gli account applicativi e le loro credenziali memorizzate nel database:
conservarlo come il database originale. Nessuna password viene stampata dalla procedura.

## 3. Installare sul nuovo PC

1. Copiare lo ZIP sul PC Windows x64.
2. Usare **Estrai tutto**: non avviare i BAT dall'interno dello ZIP.
3. Collocare la cartella `strumenti` in una posizione scrivibile dall'utente,
   per esempio `D:\Laboratorio\strumenti` o una cartella del proprio profilo.
4. Collegarsi a Internet ed eseguire `installa.bat` con doppio clic.
5. Attendere **Installazione completata**; poi avviare `strumenti.bat`.

Non occorre installare manualmente Python né modificare il PATH.
L'installer scarica uv **0.12.14** tramite l'installer ufficiale, installa Python
**3.12.13** e verifica Tkinter, CustomTkinter e Pillow.

L'installazione usa:

```text
uv python install 3.12.13 --no-bin --no-registry
uv sync --locked --no-dev --no-install-project --python 3.12.13 --managed-python
```

uv è in `.tools`, Python in `.runtime/python`, l'ambiente in `.venv` e la cache
in `.uv-cache`, tutti nella cartella estratta. Si usano percorsi espliciti;
Git e l'accesso al repository privato non sono necessari.
Riferimenti: [installer uv](https://docs.astral.sh/uv/reference/installer/)
e [sincronizzazione bloccata](https://docs.astral.sh/uv/concepts/projects/sync/).

## 4. Primo avvio e uso successivo

Accedere con un utente già presente sulla postazione sorgente e la relativa password.
L'elenco campioni è vuoto. Al primo avvio i percorsi predefiniti vengono registrati
nella nuova posizione: `sequenze`, `archiviati`, `errori`, `export`.
Le cartelle vengono create quando necessarie; per utilizzare percorsi dello strumento
o del LIS differenti, configurarli nelle **Impostazioni** con un amministratore.
Le personalizzazioni effettuate sul nuovo PC restano valide agli avvii successivi.

Aprire **Guida** per consultare il [manuale operativo](manuale.md).
Avviare sempre `strumenti.bat`, che usa `uv run --no-sync --offline python app.py`.

Non spostare la cartella dopo l'installazione: l'ambiente virtuale e i percorsi
salvati fanno riferimento alla posizione scelta. Per una nuova installazione
estrarre nuovamente lo ZIP in una cartella definitiva e rieseguire `installa.bat`.
Rieseguire l'installer nella stessa cartella non ripristina il database dello ZIP
né cancella i campioni acquisiti successivamente.

## 5. Risoluzione dei problemi

- **File obbligatorio o database mancante:** ripristinare il file sulla postazione
  sorgente. Un database non valido o uno schema non riconosciuto interrompe l'esportazione.
- **Destinazione non scrivibile/spazio insufficiente:** scegliere una cartella
  scrivibile con spazio per database temporaneo e ZIP, quindi riprovare.
- **Database occupato:** chiudere l'applicazione sorgente e riprovare.
- **Download o installazione falliti:** verificare Internet, proxy e accesso HTTPS
  ad astral.sh, GitHub (download pubblici del runtime) e PyPI. Leggere l'errore
  nella console e rieseguire `installa.bat`. Non occorrono credenziali GitHub.
- **Python o dipendenze mancanti:** rieseguire `installa.bat`; il lanciatore
  ordinario non scarica né ripara automaticamente l'ambiente.
- **Help mancante:** verificare `manuale.md` nella stessa cartella di `app.py`.
- **Sistema non supportato:** il pacchetto è dedicato a Windows AMD64, non a
  Windows a 32 bit, ARM64, Linux o macOS.

Per un primo collaudo: verificare login, lista campioni vuota, transcodifiche,
nuovi percorsi e apertura della Guida. Poi chiudere il programma e verificarne
l'avvio senza connessione Internet.
