# Strumenti LYSA 2.1 — Gestione esami non mappati e nuova strumentazione

**Versione tecnica:** 2.1.0
**Autore:** Amboni Paolo A.

## Gestione degli esami non mappati

- L'importazione prosegue conservando e segnalando i parametri senza
  transcodifica. Questi vengono ignorati nell'export LIS, senza usare il nome
  strumentale come codice esame e senza marcarli come inviati.
- Il campione passa a **Esportato** quando tutti i parametri mappati sono
  trasmessi, anche se contiene non mappati ignorati. Serve almeno un risultato
  realmente inviato: i campioni con soli non mappati restano **Da esportare**.
- Al prossimo avvio vengono riallineati automaticamente anche i campioni
  già completati. Risultati e metadati esistenti sono conservati; gli stati
  di errore non vengono modificati e il riallineamento è registrato nell'audit.
- Conteggi e preselezione considerano i soli parametri mappati pendenti;
  gli altri sono visibili nel dettaglio come **Ignorato**. Una nuova mappatura
  applicata mediante reimportazione rende nuovamente pendente il risultato.

## Nuova strumentazione

- Aggiunto il driver **Agilent 6460 LCMS**, con riconoscimento automatico
  del CSV e selezione nelle impostazioni.
- Preambolo ignorato fino a `SampleID`; acquisizione da `SampleName` (3),
  `Compound` (4) e `FinalConcentration` (6), senza ulteriori diluizioni.
- Raggruppamento per campione, prima misura utilizzabile per parametro,
  controlli e codici non validi ignorati; colonne successive alla sesta ignorate.
- Normalizzazione dei risultati e transcodifiche integrate nel flusso esistente.

## Correzioni di bug minori

- Importazione ed esportazione TXT delle transcodifiche includono ora la
  **descrizione**, conservando accenti, due punti, virgolette e ritorni a capo.
  I nuovi file hanno quattro campi; i precedenti a due/tre campi restano
  importabili senza cancellare le descrizioni esistenti.
- Corretto il ricalcolo dello stato dopo export e merge in presenza di
  parametri ignorati e allineate le indicazioni dell'interfaccia e del manuale.
- Mantenuti i controlli di completezza degli esami con sostanze: un gruppo
  incompleto o fuori catalogo viene escluso, proseguendo con gli altri esami validi.

## Database e installazione

Lo schema resta **1**. Non è richiesto un database nuovo; utenti, impostazioni,
transcodifiche e risultati esistenti vengono conservati. Il formato CSV LIS
resta invariato, con separatore punto e virgola e 24 colonne.

- Postazioni con updater: **Impostazioni → Aggiornamenti e backup**.
- Installazioni senza updater: chiudere il programma, conservare una copia
  del database e delle transcodifiche e applicare i soli file di
  `strumenti-update-2.1.0.zip`, mantenendo database e cartelle operative.
- Copie con `.git`: sincronizzare il repository e riallineare l'ambiente con
  `uv sync --locked`.

Il pacchetto aggiornamento non contiene database o dati di laboratorio.
Non usare lo ZIP di trasferimento con database ripulito per aggiornare una
postazione esistente. Le funzionalità TLS e aggiornamento della 2.0.2 restano incluse.

Dettagli: [UPDATES.md](https://github.com/AmboniRider/strumentiLysa/blob/v2.1.0/UPDATES.md).
