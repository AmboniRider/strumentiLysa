# Strumenti LYSA 2.0.2 — Correzioni updater e documentazione

**Autore:** Amboni Paolo A.

## Correzioni

- Su Windows il controllo e il download aggiornamenti usano la validazione
  nativa dei certificati tramite `truststore`/CryptoAPI, con controlli su
  certificato e hostname attivi. La catena di fiducia può recuperare gli
  intermedi mancanti tramite il sistema operativo.
- Il pannello distingue errori di certificato HTTPS, errori HTTP e timeout;
  il controllo fallito viene segnalato anche in console.
- Separati i tempi del controllo e del download: 10 secondi per richiesta
  dei metadati e fino a 5 minuti per lo ZIP, mantenendo un timeout di inattività
  di 10 secondi sul socket e i controlli di dimensione e SHA-256.
- In caso di errore di verifica, il pannello mostra istruzioni Git copiabili
  adatte sia alle copie con repository sia alle installazioni da pacchetto.
- Conservata la correzione 2.0.1 del salvataggio percorsi nelle impostazioni.

## Documentazione

- README, guida aggiornamenti, manuale e guida trasferimento aggiornati con
  la procedura Git alternativa, i controlli sul database non tracciato e la
  conservazione dei dati locali.
- Per le postazioni senza `.git`, documentati clone separato e generazione
  del solo ZIP aggiornamento con il launcher dedicato all'installazione.
- Chiariti backup preliminare, eventuali migrazioni e differenze tra ZIP
  aggiornamento e ZIP trasferimento.

## Database e compatibilità

Nessun database nuovo richiesto. Lo schema resta **1** e i dati esistenti
vengono conservati. Per le installazioni storiche con schema 0 resta disponibile
la migrazione senza perdita allo schema 1.

## Installazione

- Postazioni con updater: **Impostazioni → Aggiornamenti e backup**.
- Versioni prive di updater: chiudere il programma, salvare database e
  transcodifiche e sovrapporre i soli file di `strumenti-update-2.0.2.zip`;
  eseguire `installa.bat` per riallineare le dipendenze. Conservare
  `data/strumenti.db` e tutte le cartelle operative.
- Copie di sviluppo con `.git`: usare il normale flusso Git.
- Per errori HTTPS delle versioni precedenti: seguire la procedura Git in
  `UPDATES.md`; dopo la copia dei sorgenti eseguire `installa.bat` o
  `uv sync --locked` per installare la nuova dipendenza TLS.

Il pacchetto di aggiornamento non contiene database o dati di laboratorio.
Non usare lo ZIP di trasferimento con database ripulito per aggiornare una
postazione esistente.

Dettagli: [UPDATES.md](https://github.com/AmboniRider/strumentiLysa/blob/v2.0.2/UPDATES.md).
