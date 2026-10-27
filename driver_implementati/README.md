# 🔬 Driver Strumentali Implementati

Questa cartella raccoglie la documentazione completa e approfondita di tutti i driver di interfaccia attualmente implementati nel software per l'acquisizione dei dati analitici dagli strumenti di laboratorio.

Ciascuna guida è redatta per essere facilmente comprensibile sia dagli operatori/tecnici di laboratorio sia dagli sviluppatori software, descrivendo il formato originario dei file generati dallo strumento, la loro struttura interna, le operazioni di normalizzazione eseguite dal driver e i suggerimenti per la risoluzione dei problemi più comuni.

---

## 📋 Tabella Comparativa degli Strumenti

| Strumento | Nome nel Sistema | Formato File | Separatore | Modalità Campione | Unità di Misura nel Risultato | Normalizzazione Eseguita | Guida Dettagliata |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Agilent 6460 LCMS** | `Agilent 6460 LCMS` | CSV, nome libero | Virgola (`,`) | Multi-campione, una riga per composto | Ignorate | SampleName/Compound/FinalConcentration, prima coppia valida, extra ignorati, non numerici a 0 | [agilent_6460_lcms.md](agilent_6460_lcms.md) |
| **Agilent 5977C** | `Agilent 5977C` | CSV, nome libero | Virgola (`,`) | Multi-campione, controlli ignorati | Non presenti | Prima occorrenza valida, suffisso Results rimosso, non numerici a 0, virgola decimale | [agilent_5977c.md](agilent_5977c.md) |
| **Cromatografo Ionico Dionex** | `Cromatografo Ionico (Dionex / IC)` | `.txt` | Tabulazione (`\t`) | Singolo Campione | Non presenti (valore o `n.a.`) | `n.a.` -> `0`, virgola decimale, rimozione byte nulli NUL | [dionex_ic.md](file:///d:/pyprg/strumenti/driver_implementati/dionex_ic.md) |
| **Titolatore / Analizzatore Mettler Toledo** | `Mettler Toledo` | `ListReport.csv` | Punto e virgola (`;`) | Multi-Campione (N campioni) | Presenti (es. `uS`) | Rimozione unità di misura (es. `293,370 uS` -> `293,370`), virgola decimale, raggruppamento per ID | [mettler_toledo.md](file:///d:/pyprg/strumenti/driver_implementati/mettler_toledo.md) |
| **Spettrofotometro UV-Vis** | `Spettrofotometro (UV-Vis / Assorbanza)` | `.txt`, `.csv` | Tabulazione (`\t`), `;`, `,` | Singolo Campione | Non presenti (valori numerici) | Estrazione coppie chiave/valore o tabulari, virgola decimale | [spettrofotometro_uv_vis.md](file:///d:/pyprg/strumenti/driver_implementati/spettrofotometro_uv_vis.md) |

---

## 🛠️ Architettura e Ciclo di Vita del Driver

Tutti i driver implementano l'interfaccia astratta [`BaseInstrumentDriver`](file:///d:/pyprg/strumenti/driver.py#L19-L96) definita nel modulo [`driver.py`](file:///d:/pyprg/strumenti/driver.py).

Il servizio usa `parse_batch`, che restituisce campioni e segnalazioni prima di
salvare dati. Per i driver preesistenti un adattatore richiama `parse_samples`;
Agilent usa anche i prefissi configurati e distingue i file validi di soli
controlli dai file senza campioni utilizzabili per errori nelle colonne.

```
                      File di Sequenza nella cartella di ingresso
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │     1. Rilevamento automatico         │
                     │          (metodo can_handle)          │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │     2. Sanificazione del Testo        │
                     │ (rimozione NUL, rilevamento codifica) │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │    3. Estrazione Codice Campione      │
                     │     (18 caratteri convenzionali)      │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │    4. Estrazione & Normalizzazione    │
                     │  • rimozione unità di misura          │
                     │  • conversione non numerici a 0       │
                     │  • formattazione decimale con virgola │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │     5. Transcodifica Esame LIS        │
                     │   (associazione codice esame LIS)     │
                     └───────────────────┬───────────────────┘
                                         │
                                         ▼
                       Persistenza SQLite & Esportazione LIS
```

---

## ⚙️ Selezione del Driver Predefinito

L'utente con ruolo **Amministratore** può selezionare in qualsiasi momento il driver predefinito per il laboratorio:
1. Accedere al pannello **⚙️ Impostazioni**.
2. Selezionare la scheda **🔬 Driver Strumento**.
3. Scegliere lo strumento abituale dal menu a tendina e cliccare **Salva Preferenza**.
4. Il sistema utilizzerà il driver scelto come verificatore prioritario durante l'acquisizione automatica dei lotti.
