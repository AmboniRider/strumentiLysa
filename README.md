# strumentiLysa

Applicazione desktop locale per acquisire file di strumenti di laboratorio,
gestire campioni e risultati su SQLite ed esportare CSV per il LIS.
Supporta Dionex IC, Mettler Toledo e UV-Vis tramite driver dedicati.

**Autore:** Amboni Paolo A.

**Repository:** [AmboniRider/strumentiLysa](https://github.com/AmboniRider/strumentiLysa)

## Versione 2.0 — Major release

- **Gestione delle sostanze:** transcodifica esame/sostanza ed esportazione degli
  esami con sostanze solo se completi e coerenti con il catalogo configurato.
- **Gestione degli aggiornamenti:** controllo GitHub, pannello ADMIN, backup
  completo e ripristino in caso di errore.
- **Aggiornamento licenza e responsabilità:** AGPLv3 o successiva, attribuzione
  all'autore e disclaimer consultabili dal menu dedicato.
- **Revisione dell'interfaccia:** menu informativo, versione reale in sola
  lettura e stati visivi degli esami selezionati/già inviati.
- **Correzione di bug:** selezioni di esportazione, eliminazione utenti con
  conservazione dell'audit, primo accesso e aggiornamento del titolo finestra.

La versione tecnica è **2.0.0**. L'aggiornamento conserva il database e i dati:
non occorre scaricare un database nuovo. Dettagli in [RELEASE_NOTES.md](RELEASE_NOTES.md).

La voce **Licenza e responsabilità** nel menu principale permette a tutti gli
utenti di consultare autore, repository, disclaimer e testo integrale AGPLv3.

## Installazione e avvio

Prerequisiti: Git e `uv`. Il repository GitHub è pubblico.

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

Al primo avvio, se manca l'account `admin`, il software lo crea con ruolo
**ADMIN**, **utente `admin` e password `admin`**, anche se esistono altri utenti.
Accedere con queste credenziali e usare **Impostazioni → Gestione Utenti** per
creare nuovi account. È consigliato cambiare la password iniziale tramite
**Password**. Se `admin` esiste già, password e ruolo rimangono quelli impostati.

## Trasferimento su un nuovo PC senza Python

Su questa postazione eseguire `transfer.bat`, scegliere la cartella di destinazione
e premere **Crea ZIP**. Il pacchetto conserva utenti, impostazioni e transcodifiche;
esclude campioni, risultati, audit, file operativi e strumenti di sviluppo/Git.

Sul nuovo PC Windows x64 estrarre tutto lo ZIP in una cartella scrivibile,
eseguire `installa.bat` con Internet disponibile e poi `strumenti.bat`.
L'installer configura automaticamente uv, Python e le dipendenze locali.
Gli avvii successivi funzionano offline. Vedere [transfer.md](transfer.md).

## Sincronizzazione

Per le postazioni installate: **Impostazioni → Aggiornamenti e backup** permette
di verificare le Release, installarle e creare una copia completa del database.
All'avvio una nuova versione viene segnalata a tutti gli utenti senza bloccare
l'uso offline. Il normale aggiornamento conserva i dati; eventuali sostituzioni
del database richiedono conferma e salvano prima database e transcodifiche.
Dettagli, prima adozione e pubblicazione: [UPDATES.md](UPDATES.md).

La sincronizzazione seguente riguarda le copie di sviluppo con Git.

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

## Esclusione di garanzia e limitazione di responsabilità

Il presente software è distribuito secondo i termini della licenza GNU Affero General Public License versione 3 o successiva (AGPL-3.0-or-later).

Il software viene fornito **"COSÌ COM'È" (AS IS)**, senza alcuna garanzia esplicita o implicita, incluse, a titolo esemplificativo, le garanzie di commerciabilità, affidabilità, accuratezza dei risultati e idoneità a uno scopo particolare.

**L'utilizzatore è responsabile della valutazione dell'idoneità del software rispetto alle proprie esigenze, delle modalità del suo impiego e della verifica dei risultati ottenuti.**

Il software costituisce uno strumento di supporto operativo. L'utilizzatore è tenuto a verificare autonomamente la correttezza, l'affidabilità e l'adeguatezza dei risultati ottenuti prima del loro impiego per finalità professionali, tecniche, scientifiche o decisionali.

L'utilizzatore si assume i rischi connessi all'impiego del software, inclusi quelli relativi a malfunzionamenti, errori di elaborazione, perdita o alterazione dei dati e conseguenze derivanti dall'utilizzo dei risultati prodotti.

Nei limiti massimi consentiti dalla legge applicabile, l'autore e gli eventuali collaboratori non potranno essere ritenuti responsabili per danni diretti o indiretti derivanti dall'utilizzo o dall'impossibilità di utilizzare il software.

La presente dichiarazione integra le disposizioni delle sezioni 15, 16 e 17 della licenza GNU AGPLv3, senza modificarne i termini e senza pregiudicare le responsabilità inderogabili previste dalla legge applicabile.
