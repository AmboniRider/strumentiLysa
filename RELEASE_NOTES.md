# Strumenti LYSA 2.0.1 — Bug fix

**Autore:** Amboni Paolo A.

## Correzioni

- Corretto il pulsante **Salva Percorsi** in **Configurazione → Percorsi
  Cartelle**: il salvataggio non tenta più di leggere il campo della versione
  rimosso e non genera l'errore `AttributeError: entry_version`.
- I nuovi percorsi vengono salvati e riproposti alla riapertura della finestra.
  Driver e codici laboratorio già configurati vengono preservati, anche se
  modificati nelle altre schede durante la stessa sessione.
- La versione software resta in sola lettura e deriva dal programma installato.

## Database e compatibilità

Nessun database nuovo richiesto. Lo schema resta **1** e i dati esistenti
vengono conservati. Per le installazioni storiche con schema 0 resta disponibile
la migrazione senza perdita allo schema 1.

## Installazione

- Postazioni con updater: **Impostazioni → Aggiornamenti e backup**.
- Versioni prive di updater: chiudere il programma, salvare database e
  transcodifiche e sovrapporre i soli file di `strumenti-update-2.0.1.zip`;
  eseguire `installa.bat` per riallineare le dipendenze. Conservare
  `data/strumenti.db` e tutte le cartelle operative.
- Copie di sviluppo con `.git`: usare il normale flusso Git.

Il pacchetto di aggiornamento non contiene database o dati di laboratorio.
Non usare lo ZIP di trasferimento con database ripulito per aggiornare una
postazione esistente.

Dettagli: [UPDATES.md](https://github.com/AmboniRider/strumentiLysa/blob/v2.0.1/UPDATES.md).
