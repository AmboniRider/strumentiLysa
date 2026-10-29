# MANUALE D'USO — STRUMENTI ➔ LIS

**Autore:** Amboni Paolo A.

*Applicazione Desktop per l'Acquisizione, Normalizzazione ed Esportazione dei Dati Strumentali di Laboratorio verso il LIS*

*Aggiornato il 27 ottobre 2026 per la versione 2.1.0.*

---

## Indice del Manuale

1. [Introduzione & Scopo del Software](#1-introduzione--scopo-del-software)
2. [Strumenti Supportati & Formati File](#2-strumenti-supportati--formati-file)
3. [Interfaccia Grafica & Navigazione](#3-interfaccia-grafica--navigazione)
4. [Guida Operativa Passo-Passo](#4-guida-operativa-passo-passo)
5. [Selezione e Deselezione di Campioni e Singoli Parametri](#5-selezione-e-deselezione-di-campioni-e-singoli-parametri)
6. [Gestione dei Campioni Duplicati & Unione Intelligente (Smart Merge)](#6-gestione-dei-campioni-duplicati--unione-intelligente-smart-merge)
7. [Legenda Stati e Indicatori Visivi](#7-legenda-stati-e-indicatori-visivi)
8. [Tracciato di Esportazione LIS (CSV a 24 Colonne)](#8-tracciato-di-esportazione-lis-csv-a-24-colonne)
9. [Funzionalità Amministrative (Ruolo ADMIN)](#9-funzionalit-amministrative-ruolo-admin)
10. [Risoluzione Problemi & Domande Frequenti (FAQ)](#10-risoluzione-problemi--domande-frequenti-faq)

---

## 1. Introduzione & Scopo del Software

L'applicativo **Strumenti ➔ LIS** è stato progettato per automatizzare il passaggio delle misure analitiche prodotte dagli strumenti diagnostici del laboratorio verso il sistema informativo centrale (**LIS - Laboratory Information System**).

### Gli Obiettivi Principali
- **Eliminazione degli errori manuali**: Nessuna digitazione o trascrizione manuale dei risultati analitici da parte del personale.
- **Normalizzazione standardizzata**: Conversione automatica di codici, date, numeri decimali e parametri conformemente alle specifiche di accettazione del LIS.
- **Tracciabilità e Sicurezza**: I file grezzi degli strumenti vengono archiviati in modo permanente senza rischio di cancellazione accidentale, con log di audit su ogni esportazione.
- **Flessibilità Operativa**: Possibilità di selezionare singolarmente i campioni e i singoli test analitici da inviare, consentendo invii parziali, integrazioni e ri-esportazioni mirate.
- **Licenza Libera & Open Source**: Distribuito sotto licenza **GNU Affero General Public License v3** o successiva (`AGPL-3.0-or-later`, consultare il file `LICENSE` per i termini completi).

---

## 2. Strumenti Supportati & Formati File

Il software è dotato di un'architettura modulare a driver capace di interpretare diversi formati strumentali.

### 2.1 Cromatografo Ionico Dionex (IC)
- **Formato file**: Testo `.txt` o `.csv` delimitato da tabulazioni.
- **Struttura**: Codice campione indicato da `Sample Name:` e tabella `Component` / `Amount`. Sono supportati anche file con padding a byte nulli (`\x00`), automaticamente rimossi dal driver, come gli esempi a buffer fisso di 216 byte.
- **Dati estratti**: Codice campione a 18 caratteri (es. `BG2600036500010001`) e coppie parametro/valore presenti nella tabella degli anioni. Data/ora analisi e tempi di ritenzione non vengono acquisiti come metadati dedicati.
- **Normalizzazione**: Se un parametro non è quantificabile (`n.a.`), il software imposta il valore numerico a `0` preservando il dato grezzo.

### 2.2 Titolatore Mettler Toledo (LabX)
- **Formato file**: File CSV `ListReport.csv` delimitato da punto e virgola (`;`).
- **Struttura**: Multi-campione, contenente misure sequenziali di pH e conducibilità.
- **Dati estratti**: Identificativo a 18 caratteri estratto dalla colonna `ID campione 1`, misure analitiche ripulite automaticamente dalle unità di misura (es. `293,370 uS` diventa `293,370`).

### 2.3 Spettrofotometro UV-Vis / Assorbanza
- **Formato file**: File tabellari `.txt` o `.csv` delimitati da tabulazioni, virgole o punti e virgola.
- **Struttura**: Identificativo campione ricavato dal nome file senza estensione, che deve quindi essere un codice valido a 18 caratteri; acquisizione delle coppie parametro/valore.

### 2.4 Agilent 5977C
- **Formato file**: CSV con separatore virgola, decimali con punto e campi fra virgolette quando contengono virgole. Il nome del file è libero; numero e ordine degli esami possono variare.
- **Struttura**: Prima riga con `Sample` e nomi degli esami (es. `benzene Results`); seconda riga ignorata; dalla terza riga, un campione o controllo per riga. Il suffisso finale `Results` viene rimosso dai nomi usati nelle transcodifiche.
- **Campioni**: Solo codici conformi al validatore e ai prefissi laboratorio abilitati. Bianchi, controlli e altri codici non conformi vengono ignorati. In caso di ripetizioni nel file si conserva la prima riga utilizzabile, senza medie. I campioni già nel database seguono il merge ordinario.
- **Risultati**: Celle vuote o non numeriche diventano `0`; i valori numerici conservano le cifre decimali, con virgola nel LIS. Configurare le associazioni esame ed eventuale sostanza tramite le transcodifiche esistenti.
- **Anomalie**: Una riga campione con colonne mancanti o aggiuntive viene scartata e segnalata nel riepilogo, importando le altre righe regolari. Nomi esame duplicati o vuoti, seconda riga mancante e CSV illeggibile bloccano l'intero file prima di qualsiasi salvataggio.
- **Soli controlli**: Il file viene archiviato con un messaggio informativo e zero campioni importati. Se invece tutti i campioni sono scartati per colonne errate, il file va in `errori`.
- Dettagli e collaudo: [Scheda Agilent 5977C](driver_implementati/agilent_5977c.md).

### 2.5 Agilent 6460 LCMS
- **Formato file**: CSV con separatore virgola, nome libero e preambolo ignorato fino all'intestazione `SampleID`.
- **Dati estratti**: Codice campione da `SampleName` (colonna 3), parametro da `Compound` (colonna 4), risultato da `FinalConcentration` (colonna 6). Nessuna ulteriore diluizione; colonne successive ignorate anche se più numerose dell'intestazione.
- **Campioni**: Stesse regole sui codici e sui laboratori abilitati degli altri driver; controlli e standard non conformi ignorati. Le righe sono raggruppate per campione, conservando la prima misura utilizzabile per ciascun parametro, anche con righe non consecutive.
- **Risultati**: Nomi Compound senza spazi esterni; valori non numerici, `ND` e non finiti convertiti a `0`; virgola decimale per il LIS. Configurare le transcodifiche con i nomi Compound; tracciato LIS invariato.
- **Anomalie**: Righe di campioni validi con meno di sei colonne o Compound vuoto scartate con avviso. Intestazione incompatibile o CSV illeggibile bloccano l'intero file. Soli controlli archiviati con messaggio; soli campioni malformati inviati in `errori`.
- Dettagli e collaudo: [Scheda Agilent 6460 LCMS](driver_implementati/agilent_6460_lcms.md).

### 2.6 Percorsi di Lavoro (Cartelle)
- `sequenze/` (Input): Cartella predefinita in cui gli strumenti o gli operatori depositano i file da acquisire. La scansione considera i file `.txt`, `.csv` e `.dat` direttamente nella cartella, senza cercare nelle sottocartelle.
- `archiviati/` (Archivio): I file elaborati vengono spostati qui automaticamente. Il nome originale viene mantenuto; se esiste già un file omonimo viene aggiunto un timestamp.
- `errori/` (Scarti): Destinazione dei file per cui il parsing fallisce o nessun campione viene elaborato con successo. Per un file multi-campione con esiti misti, il file viene archiviato se almeno un campione è elaborato con successo; gli errori degli altri campioni sono riportati nel riepilogo.
- `export/` (Output LIS): Cartella in cui vengono generati i file CSV conformi al LIS pronti per l'acquisizione centrale.

Questi percorsi possono essere modificati dall'Amministratore nelle Impostazioni. Usare sempre le cartelle configurate sulla propria postazione.

---

## 3. Interfaccia Grafica & Navigazione

### Licenza e responsabilità

La voce **Licenza e responsabilità** nel menu principale è disponibile prima
del login e durante l'uso, sia per operatori sia per amministratori. La finestra
riporta l'autore **Amboni Paolo A.**, l'indirizzo del repository GitHub,
la licenza **AGPL-3.0-or-later** e il disclaimer completo, inclusa la necessità
di verificare autonomamente i risultati prima dell'impiego professionale,
tecnico, scientifico o decisionale.

La seconda scheda contiene il testo integrale AGPLv3. I testi sono consultabili
offline e copiabili, ma non modificabili. Il repository si apre nel browser solo
premendo il relativo pulsante. Il disclaimer è riportato anche in [LEGAL.md](LEGAL.md).

### Aggiornamenti e backup

All'avvio il programma verifica in background se esiste una nuova Release
stabile su GitHub. Un popup informa tutti gli utenti; gli operatori devono
rivolgersi all'amministratore. Internet assente non impedisce l'utilizzo.

Dalla versione 2.0.2 il controllo HTTPS usa la validazione nativa Windows e
segnala distintamente gli errori di certificato, HTTP e timeout. Il controllo
dei metadati mantiene il limite di 10 secondi per richiesta; il pacchetto può
impiegare fino a 5 minuti, con limite di inattività di 10 secondi sul socket.

L'amministratore trova **Aggiornamenti e backup** nelle **Impostazioni**:
può verificare manualmente, leggere le novità, installare con riavvio e creare
una copia completa datata del database in una cartella a scelta.

Prima di aggiornare vengono indicati gli effetti sul database: conservazione,
migrazione senza perdita oppure database nuovo. Quest'ultimo richiede una
conferma specifica per la perdita di campioni, risultati e audit; utenti,
impostazioni e transcodifiche compatibili vengono recuperati automaticamente.
Il programma salva prima il database completo e i canali già codificati;
il dialogo mostra la cartella `.updates/<identificativo>/`. In caso di necessità
il file `transcodifiche.txt` si importa da **Transcodifiche LIS → Importa TXT**.
Se l'aggiornamento fallisce, viene ripristinata l'installazione precedente.

La versione software è mostrata in sola lettura e viene aggiornata con il codice.
Le copie di sviluppo con Git usano il flusso Git per installare aggiornamenti.
Se il controllo fallisce, il pannello mostra nel riquadro delle note i passaggi
per aggiornare manualmente tramite Git. Con `.git` si usa `git pull --ff-only`
dopo aver controllato le modifiche locali; senza `.git` si genera lo ZIP
aggiornamento da un clone separato. Prima creare una copia del database e
chiudere l'applicazione. Il database e le cartelle operative restano locali;
il successivo avvio può applicare le migrazioni previste. La procedura manuale
non esegue il backup e il rollback automatici dell'updater.
I backup restano sul PC e non vengono caricati su GitHub; i file strumentali
esterni al database richiedono una copia separata.
Istruzioni complete e prima adozione: [Aggiornamenti](UPDATES.md).

### Primo accesso dopo l'installazione

Al primo avvio il software crea automaticamente l'account `admin` con ruolo
**ADMIN**, se questo nome utente non è già presente, anche in presenza di altri utenti.
Le credenziali predefinite sono:

- **Utente:** `admin`
- **Password:** `admin`

Dopo l'accesso, aprire **⚙️ Impostazioni → Gestione Utenti** per creare i nuovi
utenti. È consigliato modificare la password iniziale con **🔑 Password**.
Agli avvii successivi un account `admin` già presente mantiene password e ruolo:
la password personalizzata non viene reimpostata. Il nome utente viene confrontato
senza distinguere maiuscole e minuscole.

L'interfaccia si suddivide in tre aree principali:

1. **Testata Superiore (Header)**:
   - Logo e titolo applicativo.
   - Badge con indicazione dell'utente corrente e del ruolo assegnato (`OPERATORE` in verde, `ADMIN` in blu).
   - Tasti rapidi: `❓ Guida` (apre questo manuale), `🔑 Password` (per cambiare la propria password), `🚪 Esci` (logout).
   - *Se utente ADMIN*: tasti `⚙️ Impostazioni` e `🧹 Elimina Esportati`.
2. **Barra Controlli & Filtri (Toolbar)**:
   - Pulsante `📥 Carica Nuovi File` (avvia la scansione e importazione della cartella input).
   - Casella `🔍 Ricerca Testuale` (filtra in tempo reale per codice campione, accettazione, laboratorio).
   - Filtro di Stato (`Da Esportare`, `Esportati`, `Tutti`): preimpostato su **"Da Esportare"** per mostrare prioritariamente il lavoro pendente.
   - Filtro Temporale (`Ultimo Mese`, `Ultimi 3 Mesi`, `Anno Corrente`, `Tutti`): per gestire storici ampi senza rallentamenti.
3. **Pannello Master-Detail**:
   - **Tabella Superiore (Campioni - Master)**: Mostra codice campione, laboratorio, anno, accettazione, conferimento, numero campione, data di importazione, stato LIS e numero di parametri selezionati su totali (`X/Y`).
   - **Tabella Inferiore (Parametri - Detail)**: Mostra selezione Export, stato LIS, nome parametro, codice esame LIS, valore originale, valore formattato per il CSV e stato della mappatura. Non è prevista una colonna dedicata alle unità di misura.
   - **Piede della Finestra (Footer)**: Riepilogo dei campioni e test selezionati con pulsante `📤 Esporta Selezionati per LIS`.

---

## 4. Guida Operativa Passo-Passo

### Passo 1 — Accesso al Sistema
All'avvio comparirà la maschera di autenticazione:
- Inserire il proprio **Username** e **Password**.
- Premere `Accedi` o il tasto `Invio`.

### Passo 2 — Caricamento Nuovi File Strumentali
- Assicurarsi che i file generati dagli strumenti si trovino nella cartella di input configurata (predefinita: `sequenze/`).
- Premere il pulsante `📥 Carica Nuovi File` nella barra dei controlli.
- Il software elaborerà tutti i file presenti, associando il corretto driver e mostrando al termine una finestra di riepilogo con:
  - Numero totale di file trovati.
  - Nuovi campioni registrati.
  - Campioni integrati con nuovi test (Merge intelligente).
  - Eventuali duplicati o parametri non ancora mappati.
  - Righe Agilent scartate, con nome file e numero riga, e messaggi sui file archiviati senza campioni. Questi messaggi non incrementano i campioni importati o saltati.
- I file elaborati vengono spostati in automatico nella cartella `archiviati/`.

### Passo 3 — Revisione dei Dati
- Nella tabella superiore compariranno i campioni caricati con stato `🟠 Da Esportare`.
- Cliccare su un campione per visualizzare nella tabella inferiore tutti i suoi parametri analitici.
- Verificare che i parametri presentino lo stato di transcodifica `✅ Valido`.

### Passo 4 — Selezione ed Esportazione verso il LIS
- Al caricamento dell'elenco vengono preselezionati i soli test mappati pendenti di tutti i campioni visibili, anche senza aprirne il dettaglio. I campioni senza test selezionati restano deselezionati.
- Selezionare o deselezionare i campioni desiderati (vedi capitolo successivo).
- Per un invio parziale, aprire il dettaglio dei campioni interessati e lasciare spuntati solo gli esami desiderati. Il CSV include esclusivamente i test spuntati dei campioni selezionati; i campioni con zero test selezionati vengono esclusi.
- Cliccare su `📤 Esporta Selezionati per LIS` in basso a destra: la generazione parte direttamente e al termine viene mostrato l'esito.
- Il software genera il CSV nella cartella di esportazione configurata e marca come esportati i singoli parametri inclusi. Il campione passa a `🟢 Esportato` quando tutti i suoi parametri mappati risultano esportati, con almeno un invio effettivo; i non mappati ignorati non impediscono il completamento.
- Il CSV deve essere acquisito dal LIS secondo la procedura del laboratorio. L'applicazione non riceve una conferma di acquisizione dal LIS.

---

## 5. Selezione e Deselezione di Campioni e Singoli Parametri

Il software offre un controllo granulare su ciò che viene trasmesso al LIS, sia a livello di intero campione che a livello di singolo test.

### 5.1 Selezione dei Campioni (Tabella Superiore - Master)
- **Casella di Spunta `[✓] / [ ]`**: Ogni riga campione inizia con una casella di selezione `Export`.
- **Doppio Clic con il Mouse**: Facendo doppio clic su una riga di campione si attiva o disattiva la spunta.
- **Tasto Spazio**: Selezionando una riga con le frecce della tastiera e premendo la **barra spaziatrice**, la spunta viene invertita istantaneamente.
- **Pulsanti Rapidi di Gruppo**:
  - `☑️ Seleziona Tutti`: Seleziona tutti i campioni visibili, conservando i sottoinsiemi di test già scelti. Se un campione ha zero test selezionati, ne riattiva tutti i test, anche quelli già inviati; lo stesso avviene riselezionando singolarmente quel campione.
  - `⬜ Deseleziona Tutti`: Deseleziona tutti i campioni.
- **Sincronizzazione Automatica**: Se un campione ha 0 test selezionati nel pannello inferiore, la sua casella nella tabella superiore si deseleziona automaticamente. Se si riattiva almeno un test, il campione si riseleziona.

### 5.2 Selezione dei Parametri (Tabella Inferiore - Detail)
- **Invio Parziale dei Risultati Standard**: Se per un campione sono pronti 4 parametri standard ma un quinto deve essere ripetuto o verificato, è possibile escludere solo quel singolo test. Gli esami con sostanze vengono invece esportati soltanto completi, come descritto nel capitolo 8.
- **Doppio Clic o Tasto Spazio**: Facendo doppio clic sulla riga del test o premendo la barra spaziatrice, la spunta `[✓]` viene attivata o disattivata per quel solo parametro.
- **Pulsanti Rapidi per il Campione**:
  - `Seleziona Tutti`: Seleziona tutti i parametri del campione visualizzato, inclusi quelli già esportati; usarlo quando si intende includere anche questi ultimi nel CSV.
  - `Deseleziona`: Deseleziona tutti i parametri del campione visualizzato.
- **Colonna "N. Parametri"**: Nella tabella superiore compare il conteggio dinamico in formato `X/Y` (es. `3/4` indica che 3 parametri su 4 sono selezionati per l'invio).
- **Selezioni indipendenti**: Ogni campione conserva il proprio insieme di test spuntati passando da un dettaglio all'altro. Cambiare i filtri conserva le selezioni dei campioni ancora visibili e non aggiunge test a un insieme già preparato. Il pulsante di aggiornamento dell'elenco e una nuova importazione ripristinano invece la preselezione dei test pendenti.

---

## 6. Gestione dei Campioni Duplicati & Unione Intelligente (Smart Merge)

Uno dei punti di forza dell'applicativo è la gestione fluida e sicura dei **campioni duplicati**.

### Cosa Succede Quando un File Contiene un Campione Già Registrato?
In laboratorio accade frequentemente che uno strumento ri-analizzi un campione per determinare parametri diversi, oppure che lo stesso campione venga processato su strumenti distinti (es. Dionex per anioni e Mettler Toledo per pH e conducibilità).

Invece di bloccare l'acquisizione o sovrascrivere distruttivamente i dati:
1. **Nessun Blocco Interattivo**: L'acquisizione procede senza interruzioni e senza fastidiosi popup bloccanti.
2. **Unione Intelligente dei Test**:
   - Il confronto usa il nome del parametro fornito dallo strumento, senza distinguere maiuscole e minuscole e ignorando gli spazi iniziali e finali; non usa direttamente i codici LIS di esame o sostanza.
   - **Nuovi Parametri**: Se mappati vengono aggiunti con stato `🟠 Da Inviare`; se non mappati restano conservati come `⚪ Ignorato` e non riaprono un campione già completato.
   - **Parametri Esistenti non ancora Esportati**: Il valore analitico viene aggiornato all'ultima misura rilevata dallo strumento.
   - **Parametri Già Esportati al LIS**: Il valore viene aggiornato alla nuova misura, mentre il timestamp dell'ultima esportazione e lo stato `🟢 Inviato` vengono conservati. La modifica del valore non riapre automaticamente il test per una nuova esportazione.
   - **Parametri assenti nel nuovo file**: Rimangono nel campione con i dati e lo stato già registrati.
3. **Selezione dei Risultati da Esportare**:
   - Al caricamento dell'elenco sono selezionati solo i parametri mappati ancora pendenti; quelli già inviati e i non mappati sono deselezionati (`[ ]`). Aprire un dettaglio non modifica le spunte.
   - Controllare il dettaglio di ogni campione prima dell'esportazione: i comandi di selezione di tutti i test possono includere anche risultati già esportati.
   - *Nota*: Se l'operatore intende volontariamente inviare una rettifica di un test già inviato, può riattivare manualmente la spunta `[✓]`.
4. **Ripristino dello Stato del Campione**:
   - Se un campione era già `🟢 Esportato` ma riceve nuovi test mappati da uno strumento, il suo stato torna automaticamente a `🟠 DA_ESPORTARE`. Aggiungere solo non mappati non lo riapre. Configurare un parametro prima ignorato e reimportarlo lo rende invece nuovamente pendente.
   - La colonna `N. Parametri` mostra il conteggio dei parametri selezionati sul totale (`X/Y`); nel dettaglio si distinguono i test `Da Inviare` da quelli `Inviato`.
   - Il campione riappare immediatamente nella visualizzazione predefinita pronto per essere esportato!
5. **Completamento del Campione**:
   - Quando **tutti i parametri mappati** risultano inclusi in un'esportazione CSV, il campione passa a `🟢 Esportato`, anche se conserva non mappati ignorati. Serve almeno un risultato effettivamente inviato: un campione con soli non mappati resta `Da Esportare`.

**Esempio con sostanza**: una sostanza già inviata aveva valore `10`; un nuovo file riporta `12` per lo stesso nome parametro. Il database mostra `12`, ma conserva lo stato `Inviato` e il timestamp precedente: il LIS non riceve automaticamente il nuovo valore. Per trasmettere la rettifica occorre selezionare manualmente tutte le sostanze dell'esame e riesportarle, secondo i controlli di completezza descritti nel capitolo 8.

**Esempio**: un parametro Cloruri è stato esportato con valore `12,3`. Un nuovo file riporta Cloruri `12,8` e aggiunge un test pH. Dopo il merge, Cloruri mostra `12,8` ma resta `Inviato` con il timestamp precedente; il pH è `Da Inviare`. Per esportare anche la rettifica di Cloruri, l'operatore deve selezionarlo nel dettaglio. Lo stato `Inviato` non garantisce che il valore attualmente visualizzato sia quello contenuto nel CSV precedente.

---

## 7. Legenda Stati e Indicatori Visivi

| Indicatore | Posizione | Significato |
|---|---|---|
| `[✓]` / `[ ]` | Master / Detail | **Selezionato per l'Invio**: Il campione o il parametro verrà incluso nel file CSV generato per il LIS. |
| `🟠 Da Esportare` | Tabella Campioni | Restano parametri mappati da inviare, oppure non esiste ancora alcun invio effettivo (anche nel caso di soli non mappati). |
| `🟢 Esportato` | Tabella Campioni | Tutti i parametri mappati sono inclusi in un'esportazione CSV, con almeno un invio effettivo. I non mappati non bloccano il completamento; non indica conferma di ricezione dal LIS. |
| `🟠 Da Inviare` | Tabella Parametri | Il singolo test analitico è nuovo o non ancora esportato nel tracciato LIS. |
| `🟢 Inviato` | Tabella Parametri | Il test è stato incluso in un'esportazione CSV. Dopo un merge il valore può essere stato aggiornato senza una nuova esportazione. |
| `⚪ Ignorato` | Tabella Parametri | Il parametro non ha una transcodifica utilizzabile: resta conservato, senza essere esportato o conteggiato tra i pendenti. |
| `✅ Valido` | Tabella Parametri | Il parametro strumentale è mappato correttamente su un codice riconosciuto dal LIS. |
| `⚠️ Non Mappato` | Tabella Parametri | Il parametro strumentale non è presente nella tabella transcodifiche; richiede l'intervento dell'Amministratore. |

---

## 8. Tracciato di Esportazione LIS (CSV a 24 Colonne)

L'esportazione verso il LIS genera un file con nome `ESPORTAZIONE_YYYYMMDD_HHMMSS.csv` nella cartella configurata (predefinita: `export/`). Ogni riga dati corrisponde a un parametro selezionato di un campione.

### Regole Strutturali del Tracciato
- **Delimitatore di campo**: Punto e virgola (`;`).
- **Codifica caratteri**: UTF-8 standard.
- **Formato dei Numeri Decimali**: Virgola come separatore decimale (formato italiano, es. `12,35`).
- **Terminatori di riga**: CRLF.
- **Valori non numerici**: Valori quali `n.a.`, `ND` o testi privi di un valore numerico vengono normalizzati a `0`. Per Dionex e UV-Vis, anche un testo come `< 0.05` diventa `0`; il driver Mettler estrae invece la prima componente numerica, quindi `< 0.05` diventa `0,05` senza conservare il segno `<`.
- **Valore originale**: Per Dionex e UV-Vis è disponibile nel dettaglio del campione; per Mettler viene memorizzato il valore numerico ripulito dalle unità. Il CSV non include il testo originale nel campo `RISULTATO`, che resta vuoto.

### Schema delle Colonne LIS

| Posizione | Intestazione | Contenuto |
|---|---|---|
| 1 | `ANNO` | Anno a quattro cifre, es. `2026`. |
| 2 | `ACCETTAZIONE` | Cinque cifre estratte dal codice campione, con gli zeri iniziali. |
| 3 | `CONFERIMENTO` | Numero senza zeri iniziali. |
| 4 | `CAMPIONE` | Numero senza zeri iniziali. |
| 5 | `ALIQUOTA` | Vuoto. |
| 6 | `UNITÀ CAMPIONARIA` | Vuoto. |
| 7 | `N. RISULTATO` | Vuoto. |
| 8 | `SEGNO` | Vuoto. |
| 9 | `VALORE` | Valore formattato dal driver per gli standard; vuoto nelle righe con sostanza. |
| 10 | `RISULTATO` | Vuoto. |
| 11 | `TIPO ESAME` | Codice esame LIS configurato; i parametri senza transcodifica sono esclusi dall'export. |
| 12 | `ESITO` | Vuoto. |
| 13 | `UNITÀ BGSURA` | Vuoto; questa è l'intestazione attualmente generata. |
| 14 | `DATA INIZIO` | Vuoto. |
| 15 | `DATA FINE` | Vuoto. |
| 16 | `SOSTANZA` | Codice sostanza LIS configurato per il parametro; vuoto per gli standard. |
| 17 | `RISULTATO SOSTANZA` | Vuoto. |
| 18 | `VALORE SOSTANZA` | Valore formattato dal driver nelle righe con sostanza; vuoto per gli standard. |
| 19 | `SEGNO SOSTANZA` | Vuoto. |
| 20 | `INCERTEZZA SOSTANZA` | Vuoto. |
| 21 | `GERME` | Vuoto. |
| 22 | `RILEVATO GERME` | Vuoto. |
| 23 | `VALORE GERME` | Vuoto. |
| 24 | `CODICE CAMPIONE` | Codice completo a 18 caratteri. |

### Parametri senza transcodifica

L'importazione prosegue anche se un parametro strumentale non è configurato:
il risultato viene conservato e segnalato come **Non Mappato**. Durante l'export
LIS viene ignorato, senza usare il nome del composto come codice esame. Gli
altri risultati configurati continuano a essere esportati; i parametri esclusi
sono riepilogati e registrati nell'audit, senza essere marcati come inviati.
I non mappati non impediscono al campione di diventare `ESPORTATO` quando tutti
i risultati mappati sono stati inviati; i loro flag individuali restano non inviati.
Un campione con soli non mappati resta `DA_ESPORTARE`, perché non ha trasmesso nulla.
Al prossimo avvio, i campioni già bloccati solo dai non mappati vengono
riallineati automaticamente, conservando risultati e metadati d'invio esistenti.
Se tutti i risultati selezionati sono privi di transcodifica, non viene creato
alcun CSV. Dopo aver configurato i parametri, reimportare il file per aggiornare
le associazioni salvate: le modifiche alla configurazione non riscrivono lo storico.

### Esami con più Esiti (Sostanze)

Ogni sostanza ha un nome parametro distinto nel file strumentale. L'Amministratore
associa quel nome a un **Codice Esame LIS** e a un **Codice sostanza LIS** facoltativo.
Più parametri possono condividere lo stesso codice esame con codici sostanza diversi.
Il codice sostanza viene inserito nella colonna `SOSTANZA`, il risultato in
`VALORE SOSTANZA`; `TIPO ESAME` conserva il codice esame e `VALORE` resta vuoto.
Le colonne `ESITO` e `RISULTATO SOSTANZA` restano vuote. Separatore, intestazioni e
normalizzazione numerica sono gli stessi degli esami standard.

**Prima di usare un esame con sostanze, configurare tutte le sue sostanze richieste.**
L'elenco delle transcodifiche attive di quell'esame costituisce il catalogo obbligatorio.
La selezione resta individuale: per inviare l'esame devono essere presenti e selezionate
tutte le sostanze del catalogo corrente, con un solo risultato per ciascun codice.
I campioni con almeno un esame a sostanze presenti ma incomplete sono evidenziati
in rosso e inizialmente deselezionati. Possono essere selezionati manualmente per
inviare altri esami validi; l'esame incompleto resta escluso dall'esportazione.
Se manca una sostanza, una spunta è disattivata, un codice è duplicato o è fuori
catalogo, viene saltato l'intero esame. Gli altri esami completi e gli standard vengono
comunque esportati. Se l'esame è interamente deselezionato, non viene richiesto alcun invio.

Il riepilogo identifica campione, esame e sostanze mancanti/non selezionate o altri
motivi di esclusione. Le esclusioni sono registrate nell'audit; soltanto le righe
effettivamente scritte nel CSV aggiornano gli stati di invio e i conteggi.
Se non rimane alcun risultato esportabile, non viene creato il CSV.

I codici esame e sostanza sono salvati all'importazione: modificare le regole non
rimappa i risultati già acquisiti. Per aggiornarli occorre reimportare il file originale.
La verifica di completezza usa comunque il catalogo attivo corrente: dopo una modifica
controllare i codici nel dettaglio e riallineare i risultati prima dell'invio.
Una nuova misura di una sostanza già inviata mantiene stato e timestamp precedenti.
Per una rettifica, selezionare manualmente tutte le sostanze dell'esame e riesportarlo.

---

## 9. Funzionalità Amministrative (Ruolo ADMIN)

Gli utenti con ruolo `ADMIN` hanno accesso al pannello `⚙️ Impostazioni` con schede dedicate alla configurazione avanzata del sistema.

### 9.1 Transcodifiche LIS
- Permette di mappare i nomi dei parametri restituiti dagli strumenti (es. `Cloruri`) nel rispettivo codice atteso dal LIS (es. `CL_IC`).
- **Aggiunta e Modifica**: Possibilità di aggiungere nuove regole o modificare quelle esistenti tramite doppio clic sulla riga o con il pulsante `✏️ Modifica Regola`.
- **Codice sostanza LIS**: Facoltativo per gli standard, necessario per ogni sostanza di un esame con più esiti. Accetta lettere e cifre, conserva maiuscole/minuscole e zeri iniziali e rimuove solo gli spazi esterni. Una coppia esame/sostanza può essere usata da una sola regola attiva.
- **Ordinamento**: Cliccando sull'intestazione di qualsiasi colonna è possibile ordinare alfabeticamente o per ID (▲/▼).
- **Import/Export**: Il backup `transcodifica.txt` comprende sempre quattro campi: `Parametro:CodiceLIS:CodiceSostanza:Descrizione`, anche se la descrizione è vuota. Per gli esami standard lasciare vuoto il terzo campo: `Parametro:CodiceLIS::Descrizione`. Il file esportato inserisce automaticamente le virgolette CSV quando un campo contiene due punti, virgolette o ritorni a capo; le virgolette interne sono raddoppiate.
- **Compatibilità TXT**: Sono ancora accettate le righe `Parametro:CodiceLIS` e `Parametro:CodiceLIS:CodiceSostanza`. Se il quarto campo è assente, una descrizione esistente viene conservata; se è presente ma vuoto, viene cancellata. Una riga a due campi rende standard anche una regola già esistente con sostanza. Le regole nuove senza descrizione hanno testo vuoto. Righe vuote e commenti esterni con `#` vengono ignorati; errori, quoting non valido e duplicati annullano l'intera importazione senza modifiche parziali.

Esempio TXT con descrizioni:

```text
Fluoruri:BG00594::Fluoruri nelle acque
Methamidophos:BG00611:00500:Residuo di Methamidophos
Parametro:STANDARD::"Descrizione con due punti: nota"
```

### 9.2 Driver Strumento Predefinito
- Permette di impostare quale driver utilizzare in via preferenziale tra quelli registrati (`Dionex IC`, `Mettler Toledo`, `Spettrofotometro UV-Vis`).

### 9.3 Gestione Utenti
- Creazione di nuovi account di laboratorio.
- Assegnazione dei ruoli (`OPERATORE` per attività quotidiana di import/export, `ADMIN` per configurazione e manutenzione).
- Modifica ruoli, reset password e rimozione utente.
- Ordinamento dinamico della griglia utenti per username, ruolo o data creazione.

### 9.4 Manutenzione Dati (`🧹 Elimina Esportati`)
- Consente di liberare spazio nel database rimuovendo i campioni storici **già esportati** al LIS a partire da una certa data.
- **Sicurezza**: I file originali nelle cartelle `archiviati/` ed `export/` **non vengono mai eliminati**.
- **Anteprima**: Prima di procedere, viene mostrata la griglia con l'elenco esatto dei campioni che verranno rimossi e una richiesta di conferma esplicita.
- **Audit**: L'operazione viene registrata indelebilmente nel log eventi.

---

## 10. Risoluzione Problemi & Domande Frequenti (FAQ)

### D: Un parametro mostra l'etichetta `⚠️ Non Mappato`. Posso esportare il campione?
**R:** Sì, per gli altri parametri configurati. Quello non mappato viene conservato e segnalato, ma escluso dal CSV e non marcato come inviato. Se tutti i parametri selezionati sono non mappati, non viene creato alcun CSV. Contattare un Amministratore per aggiungere la regola nella scheda `⚙️ Impostazioni` ➔ `Transcodifiche LIS`, quindi reimportare una copia del file originale: la nuova regola non aggiorna automaticamente i risultati già acquisiti.

### D: Perché un campione già inviato ieri è riapparso nell'elenco "Da Esportare"?
**R:** Significa che è stato caricato un nuovo file strumentale per quel codice campione contenente nuovi parametri non presenti in precedenza (Smart Merge). Il sistema vi segnala che ci sono nuovi test pronti da trasmettere. I test vecchi saranno già contrassegnati come `🟢 Inviato` e deselezionati.

### D: Un file è finito nella cartella `errori/`. Cosa significa?
**R:** Significa che il file non conteneva un codice campione valido a 18 caratteri oppure che la struttura interna del file era danneggiata o non conforme a nessun driver strumentale disponibile. Verificare il file con Blocco Note o contattare l'assistenza tecnica.

### D: Posso re-inviare un parametro già esportato se ho corretto una misura?
**R:** Sì. Se il campione è già esportato, impostare il filtro di stato su `Esportati` o `Tutti` e scegliere un periodo che lo includa. Aprire il dettaglio, attivare la spunta del parametro con doppio clic o `Spazio`, verificare che anche il campione sia selezionato e controllare le altre spunte. L'esportazione genera un nuovo CSV con il valore attualmente registrato. Una nuova misura importata aggiorna il valore, ma non riattiva automaticamente l'esportazione di un test già `Inviato`.

### D: Ho dimenticato la password di accesso. Come posso fare?
**R:** Rivolgersi a un utente con ruolo `ADMIN`. L'amministratore può reimpostare la password accedendo a `⚙️ Impostazioni` ➔ `Gestione Utenti`.
