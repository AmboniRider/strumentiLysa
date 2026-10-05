## Metodo di lavoro

- Prima di modificare codice, analizza la struttura del progetto.
- Se il compito è complesso, proponi un piano sintetico prima di intervenire.
- Crea o aggiorna un file `PROJECT_CONTEXT.md` nella root del progetto in cui registri l'architettura. Struttura attesa:
  - **Project Goal**: Scopo sintetico dell'applicazione.
  - **Stack**: Linguaggio (Python), framework, database, OS target.
  - **Main Components**: Mappa dei file principali e delle loro responsabilità.
  - **Development Conventions**: Linee guida di design e modularità concordate.
  - **Technical Constraints**: Vincoli tecnici (es. solo locale, no cloud).
  - **Current Status & Active TODO**: Lista delle funzionalità implementate e TODO attivi.
- Crea o aggiorna un file `SESSION_SUMMARY.md` in cui registri l'andamento della sessione:
  - **Decisions and Activities**: Decisioni architetturali prese e attività svolte.
  - **Issues and Solutions**: Problemi riscontrati e come sono stati risolti.

## Ambiente Python

- Usa `uv` per creare e gestire virtual environment e pacchetti.
- Preferisci comandi riproducibili.
- Se esiste un `requirements.txt`, `pyproject.toml` o `uv.lock`, rispettalo.
- Preferisci configurazioni portabili e riproducibili.
- Preferisci l'utilizzo di `uv sync` per la creazione del virtual environment.
- Preferisci il comando `uv run` per lanciare i programmi.

## Stile e Documentazione del Codice

- **Commenti Chiari ed Esplicativi**: Commenta sempre il codice generato in modo che sia facilmente comprensibile, revisionabile e manutenibile da altri agenti AI ed eventualmente da sviluppatori umani.
- **Spiegazione delle Scelte Logiche**: Oltre a spiegare *cosa* fa il codice, chiarisci il *perché* dietro a decisioni architetturali, algoritmi non banali o gestione delle eccezioni.
- **Type Hinting e Docstring**: Utilizza le annotazioni di tipo (type hints) per le firme delle funzioni e includi docstring chiare (scopo, parametri, valori di ritorno) per classi e funzioni principali.

## Verifica

- Dopo ogni modifica significativa, indica come testarla.
- Se possibile, esegui test, lint o controlli automatici.
- Riassumi sempre i file modificati e il motivo delle modifiche.

## Interfaccia Terminale & Banner

- **Banner all'Avvio**: Ogni script Python eseguibile da terminale DEVE stampare all'avvio una cornice/box ben evidente con colori ANSI brillanti (es. Cyan/Giallo) contenente il nome del programma.
- **Titolo Finestra Terminale**: Ogni script DEVE impostare il titolo della finestra della console all'avvio (tramite sequenze ANSI `\033]0;[Titolo]\007` o `ctypes.windll.kernel32.SetConsoleTitleW`), permettendo di identificare immediatamente il ruolo di ogni terminale aperto.
- **Esempio di Riferimento**:
  ```python
  import os, sys

  def init_terminal(title: str):
      if os.name == 'nt':
          import ctypes
          ctypes.windll.kernel32.SetConsoleTitleW(title)
      sys.stdout.write(f"\033]0;{title}\007")
      sys.stdout.flush()
      
      CYAN = "\033[96m"
      YELLOW = "\033[93m"
      RESET = "\033[0m"
      box = "═" * (len(title) + 6)
      print(f"\n{YELLOW}╔{box}╗{RESET}")
      print(f"{YELLOW}║   {CYAN}{title}{YELLOW}   ║{RESET}")
      print(f"{YELLOW}╚{box}╝{RESET}\n")
  ```

## Sicurezza

- Non eseguire comandi distruttivi senza mostrare prima il comando.
- Non modificare file fuori dalla cartella del progetto senza autorizzazione.
- Non salvare o esporre chiavi API, password o token.