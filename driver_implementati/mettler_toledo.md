# 🔬 Driver: Mettler Toledo

- **Nome nel Software**: `Mettler Toledo`
- **Classe Python**: [`MettlerToledoDriver`](file:///d:/pyprg/strumenti/driver.py#L264-L408) in [`driver.py`](file:///d:/pyprg/strumenti/driver.py)
- **Tipo di Strumento**: Titolatore automatico / Analizzatore multiparametrico (es. Mettler Toledo T70 con software LabX)
- **Finalità Analitica**: Misurazione simultanea di parametri chimico-fisici fondamentali: **Conducibilità elettrica specifica** e **pH**.

---

## 1. Caratteristiche del File di Origine

| Proprietà | Descrizione |
| :--- | :--- |
| **Nome File Tipico** | `ListReport.csv` (o file contenente `ListReport` nel nome, case-insensitive) |
| **Estensione File** | `.csv` (Comma-Separated Values con testo ASCII/UTF-8) |
| **Modalità Campione** | **Multi-campione**: un singolo file report può contenere un'intera serie analitica di N campioni distinti, ciascuno con più parametri |
| **Separatore di Colonna** | Punto e virgola (`;`) |
| **Unità di Misura nel File** | Presenti nel campo Risultato (es. `293,370 uS` per la conducibilità) |

---

## 2. Struttura del File Strumentale Grezzo

Il report esportato da Mettler Toledo presenta una struttura tabulare standard a 15 colonne:

1. **Riga 1**: Intestazione software `Editor risultati;;;;...` (da ignorare).
2. **Riga 2**: Sottotitolo del report `Dettagli risultato;;;;...` (da ignorare).
3. **Riga 3**: Riga di testata delle colonne:
   `ID campione 1;Titolo;Risultato;Ora creazione;Nome metodo;Strumento;Utente;...`
4. **Righe 4+**: Righe dei risultati analitici:
   - **Colonna 0 (`ID campione 1`)**: Codice campione a 18 caratteri (es. `BG2600036590010001`).
   - **Colonna 1 (`Titolo`)**: Nome del parametro analitico (es. `Conducibilita'`, `PH`).
   - **Colonna 2 (`Risultato`)**: Valore quantificato con eventuale unità di misura (es. `293,370 uS` o `7,348`).
5. **Righe di Coda**: Righe vuote e timestamp di generazione (es. `09/09/2026 10:21:35;;...;1/1;`) scartate automaticamente dal driver.

### Esempio Reale di File Grezzo (`ListReport.csv`)

```csv
Editor risultati;;;;;;;;;;;;; ;
Dettagli risultato;;;;;;;;;;;;;;
ID campione 1;Titolo;Risultato;Ora creazione;Nome metodo;Strumento;Utente;T1-;Escluso;T1+;Commento;Stato risultato complessivo;Tipo di metodo;Tipo Determinazione;Spazio di lavoro
BG2600036590010001;Conducibilita';293,370 uS;09/09/2026 10:15:16;pH Cond;T70 (T70);SystemInternal;292,768165;False;293,545168;;OK;GT;Determinazione campione TG;Spazio di lavoro A
BG2600036590020001;Conducibilita';292,990 uS;09/09/2026 10:16:56;pH Cond;T70 (T70);SystemInternal;292,768165;False;293,545168;;OK;GT;Determinazione campione TG;Spazio di lavoro A
BG2600036590030001;Conducibilita';293,110 uS;09/09/2026 10:18:37;pH Cond;T70 (T70);SystemInternal;292,768165;False;293,545168;;OK;GT;Determinazione campione TG;Spazio di lavoro A
BG2600036590010001;PH;7,348;09/09/2026 10:15:16;pH Cond;T70 (T70);SystemInternal;7,337473;False;7,385194;;OK;GT;Determinazione campione TG;Spazio di lavoro A
BG2600036590020001;PH;7,371;09/09/2026 10:16:57;pH Cond;T70 (T70);SystemInternal;7,337473;False;7,385194;;OK;GT;Determinazione campione TG;Spazio di lavoro A
BG2600036590030001;PH;7,365;09/09/2026 10:18:38;pH Cond;T70 (T70);SystemInternal;7,337473;False;7,385194;;OK;GT;Determinazione campione TG;Spazio di lavoro A
 ;;;;;;;;;;;;;;
09/09/2026 10:21:35;;;;;;;;;;;;;1/1;
```

---

## 3. Operazioni Svolte dal Driver

Il driver esegue un flusso specializzato per gestire file con più campioni e pulire i valori dalle unità di misura:

```
                  File ListReport.csv grezzo
                            │
                            ▼
          1. Riconoscimento automatico (can_handle)
             Verifica nome "ListReport" e intestazioni:
             "ID campione 1", "Titolo", "Risultato"
                            │
                            ▼
          2. Salto Intestazioni Iniziali
             Scarto delle prime 3 righe del file
                            │
                            ▼
          3. Raggruppamento Multi-Campione
             Lettura riga per riga e associazione per ID Campione
                            │
                            ▼
          4. Pulizia e Sanitizzazione del Risultato (_extract_numeric_result)
             • Rimozione unità di misura (es. "293,370 uS" -> "293,370")
             • Normalizzazione con virgola decimale per il LIS
                            │
                            ▼
          5. Transcodifica Parametri LIS
             • Conducibilita' -> BG00591
             • PH             -> BG00598
                            │
                            ▼
          6. Generazione Elenco Oggetti ParsedSample
             Restituisce N campioni pronti per l'importazione
```

### Dettaglio delle Operazioni:

1. **Riconoscimento Automatico (`can_handle`)**:
   - Controlla che il nome del file contenga la stringa `listreport` (senza distinzione tra maiuscole e minuscole).
   - Ispeziona le prime 5 righe per verificare la presenza congiunta di `id campione 1`, `titolo` e `risultato`.
2. **Supporto Multi-Campione Nativo (`parse_samples`)**:
   - A differenza dei driver mono-campione, raggruppa le righe in base al valore della prima colonna (`ID campione 1`).
   - Se il file riporta ad esempio 3 campioni, ciascuno con la misura di Conducibilità e la misura di pH in righe separate (come accade quando lo strumento esegue prima tutta la serie di conducibilità e poi la serie di pH), il driver riunisce tutti i parametri sotto il rispettivo campione.
3. **Rimozione Automatica delle Unità di Misura (`_extract_numeric_result`)**:
   - Il tracciato standard del LIS accetta unicamente valori numerici nella colonna `VALORE` (colonna 8).
   - Il software Mettler Toledo include unità come `uS`, `mS`, `pH`, `mV` direttamente nella stringa del risultato.
   - Il driver applica un'espressione regolare per estrarre la sola componente numerica (es. `'293,370 uS'` viene convertito nel numero float `293.37` e nella stringa formattata `'293,370'`).
4. **Transcodifica LIS**:
   - Associa le etichette dello strumento ai codici esame del LIS memorizzati a database:
     - `Conducibilita'` -> `BG00591`
     - `PH` -> `BG00598`
5. **Filtraggio Righe Spurie**:
   - Righe vuote, righe di commento o timestamp a fondo pagina vengono scartati automaticamente senza generare errori o falsi campioni.

---

## 4. Note Pratiche e Risoluzione Problemi per l'Operatore

- **Esportazione da LabX**: Assicurarsi di selezionare il formato report a lista standard (`ListReport`). Il file può essere salvato direttamente nella cartella di ingresso configurata (`data/ingresso/` o percorso di rete).
- **Integrazione con Misure da Altri Strumenti**: Se lo stesso campione a 18 caratteri è già stato acquisito dal Cromatografo Dionex (es. per i Solfati o Cloruri), l'importazione del `ListReport.csv` **non cancellerà i vecchi risultati**: grazie alla logica di **Unione Intelligente (Merge)**, i parametri `Conducibilita'` e `PH` verranno aggiunti al campione esistente e proposti come `🟠 Da Inviare`.
- **Modifica del Nome Parametro**: Se nello strumento il parametro viene rinominato (es. da `Conducibilita'` a `Cond`), è sufficiente aggiornare la corrispondente regola di transcodifica dal pannello **⚙️ Impostazioni -> Transcodifiche LIS** per ripristinare immediatamente l'associazione al codice LIS `BG00591`.
