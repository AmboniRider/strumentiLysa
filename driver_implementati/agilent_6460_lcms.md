# Agilent 6460 LCMS

## Formato e riconoscimento

Il driver riconosce il contenuto del report CSV, indipendentemente dal nome del
file. Il separatore è la virgola; sono supportati campi tra virgolette, UTF-8
con o senza BOM e le codifiche già gestite dal lettore condiviso.

Tutte le righe iniziali vengono ignorate fino all'intestazione `SampleID`.
I nomi richiesti devono occupare le seguenti posizioni (gli spazi esterni e
le maiuscole delle etichette sono ignorati):

| Colonna | Etichetta | Dato acquisito |
| :--- | :--- | :--- |
| 1 | `SampleID` | Firma dell'intestazione, non usato come codice campione |
| 3 | `SampleName` | Codice campione |
| 4 | `Compound` | Nome parametro |
| 6 | `FinalConcentration` | Risultato finale |

`CalculatedConcentration` non viene acquisita. Non vengono applicati fattori di
diluizione, soglie, arrotondamenti o conversioni di unità aggiuntivi. Le righe
devono avere almeno sei colonne; tutte le successive sono ignorate. Questa
regola permette di leggere il riferimento reale, con 19 etichette e 21 celle
per riga, senza scartare risultati corretti nelle colonne richieste.

```csv
Metadati iniziali ignorati
SampleID,CompoundID,SampleName,Compound,CalculatedConcentration,FinalConcentration,Dilution
0,24,bianco,Methamidophos,1.0,1.0,1
54,24,BG2600037720010001,Methamidophos,999,9.58520825918,10
55,14,BG2600037730010001,Cyromazin,999,ND,10
```

## Campioni, risultati e ripetizioni

Il validatore condiviso accetta solo codici a 18 caratteri con laboratorio
abilitato, parte numerica e filler `00`. Spazi esterni e lettere minuscole del
codice vengono normalizzati. Tutti gli altri identificativi, inclusi standard,
bianchi e controlli, sono ignorati senza creare campioni o errori.

I risultati vengono raggruppati per codice campione anche se le righe non sono
consecutive. Per ogni coppia codice-parametro si conserva la **prima riga
utilizzabile**, senza medie o sostituzioni; una riga scartata non prenota la
coppia. Il nome Compound conserva maiuscole, punteggiatura e spazi interni;
vengono eliminati soltanto gli spazi esterni.

Il valore grezzo resta disponibile. Celle vuote, `ND`, altri testi, NaN e
infinito producono `0`. I numeri mantengono le cifre originali con virgola
decimale per il LIS: `9.58520825918` diventa `9,58520825918`. Anche un valore
convertito a zero conta come prima misura utilizzabile.

Configurare le transcodifiche usando i nomi Compound, ad esempio `Methamidophos`.
L'associazione a esami standard e sostanze usa il flusso esistente; nessun codice
LIS viene precaricato. I parametri non mappati vengono conservati e segnalati
durante l'importazione, ma ignorati nell'export LIS: non sono scritti nel CSV
né marcati come inviati e non bloccano gli altri risultati. Se non esiste alcun
risultato esportabile, non viene creato il file. Per associare i dati già
acquisiti dopo aver configurato un parametro, reimportare il report.
Le sostanze fuori catalogo o i gruppi incompleti mantengono la regola esistente:
si esclude l'intero esame interessato, proseguendo con gli altri esami validi.
I campioni già presenti seguono il merge del servizio di importazione.

Il campione nel suo complesso passa a `ESPORTATO` quando tutti i risultati
mappati sono inviati, anche se rimangono non mappati ignorati. Un campione con
soli non mappati resta `DA_ESPORTARE`: serve almeno un risultato realmente
trasmesso. I campioni storici bloccati solo dagli ignoti vengono riallineati
al prossimo avvio senza marcare come inviati gli ignoti stessi.

## Errori e archiviazione

| Caso | Esito |
| :--- | :--- |
| Intestazione assente o colonne richieste incompatibili | Intero file in `errori`, nessun salvataggio |
| CSV illeggibile, anche dopo righe valide | Intero file in `errori`, nessun salvataggio |
| Campione valido con meno di sei celle o Compound vuoto | Riga scartata con numero originale nel riepilogo; importate le altre righe |
| Colonne oltre la sesta | Ignorate, senza avvisi |
| Identificativo non valido o riga senza la terza colonna | Ignorata |
| Soli controlli o tabella senza dati | File archiviato con messaggio informativo |
| Solo righe campione malformate | File in `errori` con avvisi |

Il parser completa il batch prima di restituire i risultati al servizio, evitando
salvataggi parziali in presenza di errori globali. Gli scarti di riga non
incrementano il conteggio dei campioni saltati.

## API e collaudo

`parse_batch(file_path, transcode_map=None, allowed_labs=None)` restituisce
`ParsedBatch` con campioni, avvisi e `archive_if_empty`. `parse_samples` restituisce
la lista; `parse_file` il primo campione, oppure `ValueError` se non ce ne sono.
Senza `allowed_labs` si usano i prefissi predefiniti del validatore.

Eseguire `uv run pytest tests/test_agilent6460.py tests/test_transfer.py -q`.
I test lavorano su copie e database temporanei. Il riferimento
`esempi/Agilent6460LCMS.csv` deve produrre i campioni `BG2600037720010001` e
`BG2600037730010001`, 41 risultati ciascuno, quattro `ND` convertiti a zero.
Il formato LIS resta CSV con punto e virgola e 24 colonne.
