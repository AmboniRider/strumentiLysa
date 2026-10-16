# Agilent 5977C

## Formato e riconoscimento

Il driver **Agilent 5977C** riconosce il contenuto del report, indipendentemente
dal nome del file. Il formato supportato è CSV con separatore virgola, decimali
con punto e virgolette CSV per campi contenenti virgole. Sono supportati UTF-8
con o senza BOM e le codifiche di testo già gestite dagli altri driver.

- Prima riga: `Sample` nella prima colonna e nomi esame nelle successive;
  almeno un esame deve avere il suffisso finale `Results`.
- Seconda riga: ignorata, anche se contiene etichette diverse da `Final Conc.`.
- Dalla terza riga: identificativo nella prima colonna, un risultato per ogni
  colonna esame. Numero, nomi e ordine degli esami possono cambiare.
- Le righe vuote sono ignorate. Il nome esame viene ripulito dagli spazi esterni
  e dal solo suffisso finale `Results`, senza alterare il nome chimico.

Esempio sintetico:

```csv
Sample,benzene Results,"1,2-dicloroetano Results"
Name,Final Conc.,Final Conc.
CQ inizio,0.5000,0.5000
BG2600143100010001,0.0128,0.0000
```

## Campioni, controlli e ripetizioni

Il servizio passa al driver i prefissi laboratorio configurati nelle impostazioni.
Il codice deve superare l'intera validazione esistente: 18 caratteri, laboratorio
abilitato, parte numerica e filler `00`. Spazi esterni e lettere minuscole del
codice vengono normalizzati dal validatore. Tutti gli identificativi non conformi,
inclusi BLK e CQ, sono ignorati senza salvarli o esportarli.

Per ciascun codice si conserva **la prima riga utilizzabile nel file**. Le
successive misure sono ignorate, senza medie o sostituzioni. Una prima riga con
colonne mancanti o aggiuntive viene scartata e non impedisce di acquisire una
successiva riga regolare. Per un campione già nel database resta la gestione
esistente: merge automatico dalla GUI, oppure conferma se richiesta dal chiamante.

## Risultati e transcodifiche

Il dato grezzo resta disponibile. Celle vuote e testi (`ND`, `n.a.`, altri testi)
producono `0`; anche NaN e valori infiniti vengono convertiti a zero.
I numeri conservano le cifre originali: `0.0000` diventa `0,0000`, `0.6568`
diventa `0,6568`. Non si applicano soglie, arrotondamenti o conversioni di unità.

Le transcodifiche si configurano usando i nomi ripuliti, ad esempio `benzene` e
`1,2-dicloroetano`. È possibile associare un esame LIS standard oppure un esame
con codice sostanza, attraverso le funzioni già presenti. I parametri non mappati
sono acquisiti e segnalati secondo il flusso ordinario. Nessun codice LIS viene
precaricato o dedotto da questo esempio.

## Scarti e archiviazione

| Caso | Esito |
| :--- | :--- |
| Riga campione con numero di colonne errato | Riga scartata, numero riga nel riepilogo; importazione delle altre righe |
| Nomi esame duplicati dopo pulizia, anche con maiuscole diverse | Intero file in `errori`, nessun campione salvato |
| Nome esame vuoto, seconda riga mancante o CSV illeggibile | Intero file in `errori`, nessun campione salvato |
| File valido con soli controlli/identificativi ignorati, o senza righe dati | Archivio e messaggio informativo, zero campioni ed errori |
| Tutte le righe campione scartate per colonne errate | File in `errori`, con dettaglio degli scarti |
| Almeno un campione elaborato o duplicato gestito | Archivio secondo le regole ordinarie |

Il driver legge l'intero CSV prima di restituire il batch: anche una virgoletta
non chiusa alla fine impedisce il salvataggio delle righe precedenti. Le righe
scartate sono avvisi di file e non incrementano il conteggio dei campioni saltati.

## API e verifica

`parse_batch(file_path, transcode_map=None, allowed_labs=None)` restituisce un
`ParsedBatch` con `samples`, `warnings` e `archive_if_empty`. Se i laboratori non
sono specificati si usano quelli predefiniti del validatore. `parse_samples`
mantiene l'interfaccia a lista; `parse_file` restituisce il primo campione oppure
solleva `ValueError` se non ce ne sono. L'adattatore base degli altri driver
mantiene `archive_if_empty=False` e non ne cambia il comportamento.

Test: `uv run pytest tests/test_agilent.py -q`. I test usano copie del file
`esempi/Agilent5977C.csv`, report sintetici e database temporanei. Il riferimento
deve produrre 4 campioni distinti con 9 risultati ciascuno; il cloroformio del
campione ripetuto `BG2600143100010001` deve essere `0,6568`.
