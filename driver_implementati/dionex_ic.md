# 🧪 Driver: Cromatografo Ionico (Dionex / IC)

- **Nome nel Software**: `Cromatografo Ionico (Dionex / IC)`
- **Classe Python**: [`DionexICDriver`](file:///d:/pyprg/strumenti/driver.py#L98-L191) in [`driver.py`](file:///d:/pyprg/strumenti/driver.py)
- **Tipo di Strumento**: Cromatografo Ionico da laboratorio (Thermo Scientific Dionex / software Chromeleon)
- **Finalità Analitica**: Determinazione quantitativa di anioni inorganici (Fluoruri, Cloriti, Cloruri, Nitriti, Clorati, Nitrati, Solfati) e cationi in campioni acquosi.

---

## 1. Caratteristiche del File di Origine

| Proprietà | Descrizione |
| :--- | :--- |
| **Estensione File** | File di testo non formattato `.txt` o `.dat` |
| **Modalità Campione** | **Mono-campione**: ciascun file contiene i risultati di una singola iniezione/campione analitico |
| **Separatore di Colonna** | Tabulazione (`\t`) |
| **Nome File Tipico** | Denominato con il codice campione a 18 caratteri (es. `BG2600104420010001.txt`) |
| **Codifica & Dimensione Buffer** | Testo ASCII/ANSI a lunghezza fissa di 216 byte, terminato con padding di byte nulli (`\x00` / NUL) generati dal modulo di esportazione dello strumento |

---

## 2. Struttura del File Strumentale Grezzo

Il file generato dal Dionex IC è organizzato in blocchi rigidi separati da tabulazioni:

1. **Riga 1**: Intestazione con etichetta `Sample Name:` seguita dal codice campione a 18 caratteri.
2. **Righe 2-8**: Linee vuote o metadati secondari dell'iniezione.
3. **Riga 9**: Riga di testata della tabella dei componenti analitici: `Component\tAmount`.
4. **Righe 10-11**: Righe vuote separatrici.
5. **Righe 12-18**: Righe dei dati analitici composte da `NomeParametro\tValore`.
6. **Righe 19-27**: Spaziatori finali con padding di caratteri `\x00` fino a saturare il buffer fisso dello strumento.

### Esempio Reale di File Grezzo (`BG2600104420010001.txt`)

```text
Sample Name:	BG2600104420010001
	
	
	
	
	
	
	
Component	Amount 
	
	
Fluoruri	n.a.
Cloriti	n.a.
Cloruri	0,7733
Nitriti	n.a.
Clorati	n.a.
Nitrati	8,6948
Solfati	3,8142
	
	
	
	
	
	
	
	
```

---

## 3. Operazioni Svolte dal Driver

Il driver esegue una sequenza automatizzata di 6 passaggi per trasformare il file nel tracciato LIS standard:

```
                  File .txt Dionex grezzo
                            │
                            ▼
          1. Riconoscimento automatico (can_handle)
             Verifica presenza stringa "Sample Name:"
                            │
                            ▼
          2. Sanitizzazione e rimozione byte NUL
             Eliminazione byte \x00 e gestione codifica
                            │
                            ▼
          3. Estrazione Codice Campione (18 car.)
             Parsing da riga "Sample Name:" o nome file
                            │
                            ▼
          4. Parsing Tabella Componenti (dopo "Component")
             Lettura coppie Parametro / Valore
                            │
                            ▼
          5. Normalizzazione Valori Numerici
             • "n.a." / "ND" -> convertiti in 0 ("0")
             • Numeri -> formato con virgola decimale (es. 0,7733)
                            │
                            ▼
          6. Transcodifica Codice Esame LIS
             Associazione parametro -> codice LIS (es. Solfati -> BG00596)
```

### Dettaglio delle Operazioni:

1. **Riconoscimento Automatico (`can_handle`)**:
   - Ispeziona le prime 5 righe del file: se trova il token `Sample Name:`, dichiara compatibilità con il file.
2. **Sanitizzazione Padding NUL (`_read_text_file`)**:
   - Il firmware Dionex esporta a buffer fisso riempito con byte `\x00`. Il driver pulisce trasparentemente tutti i caratteri `\x00`, prevenendo problemi di visualizzazione (es. errata apertura in Blocco Note come UTF-16) e corruzioni nei database.
3. **Estrazione del Codice Campione**:
   - Estrae il testo successivo a `Sample Name:` fino alla prima tabulazione. In caso di anomalia nell'etichetta, utilizza il nome del file privo di estensione come fallback.
4. **Individuazione Sezione Dati**:
   - Ricerca l'intestazione contenente `Component` e `Amount`. Tutte le righe successive non vuote vengono trattate come righe analitiche.
5. **Normalizzazione dei Valori**:
   - Parametri non quantificati o sotto il limite di rilevabilità (`n.a.`, `na`, `nd`, `-`) vengono convertiti in valore numerico `0.0` e stringa formattata `"0"`, come tassativamente richiesto dal tracciato LIS.
   - Parametri quantificati (es. `0,7733`, `8,6948`) mantengono la precisione decimale con virgola.
6. **Transcodifica LIS**:
   - Ciascun parametro viene mappato con la tabella di transcodifica attiva (es. `Fluoruri` -> `BG00594`, `Cloruri` -> `BG00590`, `Nitrati` -> `BG00595`, `Solfati` -> `BG00596`). Se un parametro non è censito, viene contrassegnato con `⚠️ Non Mappato` e notificato all'operatore.

---

## 4. Note Pratiche e Risoluzione Problemi per l'Operatore

- **Denominazione del File**: Il file esportato dallo strumento può chiamarsi con il codice a 18 caratteri (es. `BG2600104420010001.txt`). In ogni caso, il driver legge in via prioritaria il codice inserito nel campo `Sample Name:` all'interno del file.
- **Visualizzazione su Windows 11**: Se si apre il file originale con il Blocco Note di Windows 11, la presenza dei byte nulli di riempimento potrebbe mostrare caratteri cinesi (mojibake). Con *Notepad++* o con il nostro applicativo il file viene visualizzato correttamente, poiché il driver sanitizza automaticamente il file durante l'acquisizione.
- **Parametri 'n.a.'**: È del tutto normale che alcuni parametri riportino `n.a.`. Il sistema li importerà impostando valore `0`, che verrà esportato correttamente nel tracciato LIS a 24 colonne.
