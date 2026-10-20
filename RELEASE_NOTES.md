# Strumenti LYSA 2.0.0 — Major release

**Autore:** Amboni Paolo A.

La versione 2.0 raccoglie l'evoluzione delle funzionalità di laboratorio,
degli aggiornamenti e dell'interfaccia.

## Novità principali

- **Gestione delle sostanze:** associazione dei parametri a codice esame e
  codice sostanza LIS, con controllo di completezza e coerenza del catalogo
  prima dell'esportazione. Il tracciato LIS resta di 24 colonne separate da `;`.
- **Gestione degli aggiornamenti:** controllo delle Release GitHub all'avvio,
  pannello ADMIN **Aggiornamenti e backup**, copie complete verificate e
  installazione con ripristino automatico in caso di errore.
- **Aggiornamento licenza e responsabilità:** attribuzione all'autore,
  disclaimer sul supporto operativo e sulla verifica autonoma dei risultati;
  menu **Licenza e responsabilità** con testo integrale AGPLv3 e repository,
  disponibile per tutti gli utenti anche prima del login.
- **Revisione dell'interfaccia:** stato visivo degli esami selezionati e già
  inviati, pannelli informativi e versione effettiva del software in sola lettura.
- **Correzione di alcuni bug:** rispetto delle selezioni durante esportazione
  e reinvio, cancellazione degli utenti con conservazione dello storico audit,
  creazione di `admin` / `admin` se manca l'account e aggiornamento del titolo
  senza ricreare la schermata di login.

## Database e compatibilità

**Migrazione senza perdita di dati. Non è richiesto un database nuovo.**
Lo schema storico non versionato (0) viene portato allo schema 1; uno schema 1
esistente viene mantenuto. Utenti, password, impostazioni, transcodifiche,
campioni, risultati e audit vengono conservati. Prima dell'aggiornamento sono
previsti backup completo e salvataggio dei canali già codificati.

Questa major release non cambia la licenza del progetto: resta
**GNU Affero General Public License versione 3 o successiva (AGPL-3.0-or-later)**.

## Installazione

- Per le postazioni con updater: usare **Impostazioni → Aggiornamenti e backup**.
- Per le versioni precedenti prive di updater: chiudere l'applicazione, salvare
  database e transcodifiche, quindi sovrapporre i soli file dello ZIP
  `strumenti-update-2.0.0.zip` e riallineare le dipendenze con `installa.bat`.
  Conservare `data/strumenti.db` e tutte le cartelle operative.
- Le copie di sviluppo con `.git` si aggiornano tramite il normale flusso Git.

Non utilizzare lo ZIP di trasferimento con database ripulito per sovrascrivere
una postazione esistente. Il pacchetto di aggiornamento non contiene database
operativi, backup, credenziali o dati di laboratorio.

Installazione automatica per Windows x64, Python 3.11–3.13 e uv locale; Internet
necessario per l'aggiornamento, utilizzo ordinario disponibile offline.

Dettagli: [UPDATES.md](https://github.com/AmboniRider/strumentiLysa/blob/v2.0.0/UPDATES.md).
