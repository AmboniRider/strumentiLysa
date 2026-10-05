# 🌈 Driver: Spettrofotometro (UV-Vis / Assorbanza)

- **Nome nel Software**: `Spettrofotometro (UV-Vis / Assorbanza)`
- **Classe Python**: [`SpectrophotometerDriver`](file:///d:/pyprg/strumenti/driver.py#L194-L262) in [`driver.py`](file:///d:/pyprg/strumenti/driver.py)
- **Tipo di Strumento**: Spettrofotometro UV-Visibile da banco per letture di assorbanza, trasmittanza e concentrazione fotometrica
- **Finalità Analitica**: Dosaggi colorimetrici quantitativi (es. Ammoniaca, Silice, Fosforo totale, Tensioattivi, Metalli pesanti, COD).

---

## 1. Caratteristiche del File di Origine

| Proprietà | Descrizione |
| :--- | :--- |
| **Estensioni File Supportate** | `.txt`, `.csv`, `.dat` |
| **Modalità Campione** | **Mono-campione**: ciascun file corrisponde ad un'analisi/campione |
| **Separatori di Colonna Flessibili** | Rilevamento automatico tra Tabulazione (`\t`), Punto e virgola (`;`) o Virgola (`,`) |
| **Codice Campione** | Estratto dal nome del file (es. `BG2600104440010001.txt` -> codice `BG2600104440010001`) |
| **Commenti** | Righe con prefisso `#` ignorate automaticamente |

---

## 2. Struttura del File Strumentale Grezzo

I file generati dagli spettrofotometri presentano tipicamente una testata con la lunghezza d'onda di lavoro, seguita dalle coppie parametro/valore o da una tabella analitica:

1. **Intestazione (Opzionale)**: Metadati contenenti parole chiave come `Wavelength`, `Absorbance` o `UV-Vis`.
2. **Commenti (Opzionali)**: Righe descrittive che iniziano con `#`.
3. **Righe Dati**: Coppie separate da delimitatore:
   - Colonna 1: Nome del parametro o della determinazione (es. `Ammoniaca`, `Silice`, `Fosforo_Totale`).
   - Colonna 2: Valore misurato o concentrazione calcolata.

### Esempio Tipico di File Grezzo (`BG2600104440010001.txt`)

```text
# Spettrofotometro UV-Vis - Metodo Colorimetrico
Wavelength: 655 nm
Parametro;Valore
Ammoniaca;0,245
Silice;1,120
Fosforo_Totale;0,035
```

---

## 3. Operazioni Svolte dal Driver

Il driver offre la massima flessibilità per adattarsi alle esportazioni di diversi modelli di spettrofotometri:

```
                  File Spettrofotometro grezzo
                            │
                            ▼
          1. Riconoscimento automatico (can_handle)
             Verifica presenza termini: "absorbance",
             "wavelength", "uv-vis" nelle prime 10 righe
                            │
                            ▼
          2. Estrazione Codice Campione
             Ricavato direttamente dal nome del file (path.stem)
                            │
                            ▼
          3. Rilevamento Automatico del Delimitatore
             Identifica \t, ; o , riga per riga
                            │
                            ▼
          4. Filtraggio Righe di Commento e Intestazioni
             Salta righe con "#" o etichette come "wavelength"
                            │
                            ▼
          5. Normalizzazione Valori Numerici
             • Gestione "n.a." o "ND" -> convertiti in 0
             • Formattazione con virgola decimale per il LIS
                            │
                            ▼
          6. Transcodifica Parametri LIS
             Mappatura parametro -> codice esame LIS (es. Ammoniaca -> BG00101)
```

### Dettaglio delle Operazioni:

1. **Riconoscimento Automatico (`can_handle`)**:
   - Analizza le prime 10 righe del file alla ricerca di termini chiave tipici delle misure spettrofotometriche (`absorbance`, `wavelength`, `uv-vis`).
2. **Estrazione del Codice Campione**:
   - Poiché i software degli spettrofotometri spesso non inseriscono il codice all'interno del report, il driver ricava il codice identificativo a 18 caratteri dal nome del file stesso (`path.stem`).
3. **Riconoscimento del Delimitatore Dinamico**:
   - Per ciascuna riga verifica prioritariamente la presenza di tabulazioni (`\t`), punto e virgola (`;`) o virgola (`,`), permettendo di importare indifferentemente file TSV o CSV.
4. **Scarto Intestazioni e Righe di Testata**:
   - Ignora righe che iniziano con `#` o le cui etichette contengono parole riservate (`sample`, `component`, `parametro`, `wavelength`).
5. **Normalizzazione e Transcodifica LIS**:
   - Applica la normalizzazione numerica con virgola decimale e converte eventuali `n.a.` a `0`.
   - Consulta la tabella transcodifiche attiva per assegnare il corrispondente codice esame del LIS.

---

## 4. Note Pratiche per l'Operatore di Laboratorio

- **Regola di Denominazione del File**: È **fondamentale** che l'operatore salvi il file esportato dallo spettrofotometro assegnandogli come nome il codice campione a 18 caratteri (es. `BG2600104440010001.txt` o `BG2600104440010001.csv`), poiché il driver utilizza il nome del file per associare i risultati all'accettazione e al conferimento.
- **Configurazione Driver di Default**: Se una postazione di lavoro è dedicata prevalentemente allo spettrofotometro, l'amministratore può impostare `Spettrofotometro (UV-Vis / Assorbanza)` come driver predefinito in **⚙️ Impostazioni -> Driver Strumento**, velocizzando la scansione.
- **Aggiunta di Nuovi Parametri**: Qualsiasi nuovo test eseguito allo spettrofotometro può essere mappato in tempo reale senza ricompilare il programma, inserendo la regola in **⚙️ Impostazioni -> Transcodifiche LIS**.
