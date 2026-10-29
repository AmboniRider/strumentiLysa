@echo off
setlocal EnableExtensions DisableDelayedExpansion
title STRUMENTI LYSA - Sincronizzazione GitHub e intranet
chcp 65001 > nul
cd /d "%~dp0"

rem Ricava ESC senza salvare credenziali o dipendere da file esterni.
for /f "delims=" %%E in ('powershell -NoProfile -Command "[char]27"') do set "SYNC_ESC=%%E"
echo %SYNC_ESC%[93m+======================================================+%SYNC_ESC%[0m
echo %SYNC_ESC%[93m^|%SYNC_ESC%[96m          STRUMENTI LYSA - SYNC GITHUB                 %SYNC_ESC%[93m^|%SYNC_ESC%[0m
echo %SYNC_ESC%[93m+======================================================+%SYNC_ESC%[0m
echo.

rem --check verifica solo i prerequisiti, senza commit o accesso alla rete.
if not "%~1"=="" if /i not "%~1"=="--check" goto usage_error
where git > nul 2>&1
if errorlevel 1 goto missing_git
where uv > nul 2>&1
if errorlevel 1 goto missing_uv
git rev-parse --is-inside-work-tree > nul 2>&1
if errorlevel 1 goto missing_repository
git remote get-url origin > nul 2>&1
if errorlevel 1 goto missing_origin

rem Evita di registrare file con conflitti o di interferire con operazioni sospese.
for /f "delims=" %%U in ('git ls-files --unmerged') do goto unfinished_operation
for %%S in (MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply) do (
    for /f "delims=" %%P in ('git rev-parse --git-path %%S') do if exist "%%P" goto unfinished_operation
)
set "SYNC_BRANCH="
for /f "delims=" %%B in ('git symbolic-ref --quiet --short HEAD') do set "SYNC_BRANCH=%%B"
if not defined SYNC_BRANCH goto detached_head
if /i "%~1"=="--check" goto check_ok

rem Registra aggiunte, modifiche e rimozioni rispettando .gitignore.
echo [1/5] Preparazione delle modifiche locali...
git add --all
if errorlevel 1 goto failure
git diff --cached --quiet
if errorlevel 2 goto failure
if errorlevel 1 (
    git commit -m "Sincronizzazione progetto %DATE% %TIME%"
    if errorlevel 1 goto failure
) else (
    echo Nessuna modifica locale da registrare.
)

echo [2/5] Lettura aggiornamenti da GitHub...
git fetch origin
if errorlevel 1 goto failure

rem Il merge preserva la storia: nessun reset, rebase o push forzato.
echo [3/5] Integrazione del ramo remoto %SYNC_BRANCH%...
git merge --no-edit "origin/%SYNC_BRANCH%"
if errorlevel 1 goto merge_failure

echo [4/5] Caricamento delle modifiche su GitHub...
git push --set-upstream origin "%SYNC_BRANCH%"
if errorlevel 1 goto failure
echo [5/5] Sincronizzazione nuove versioni intranet...
if /i not "%SYNC_BRANCH%"=="main" goto skip_intranet
rem Non riallineare le dipendenze durante il sync: usare l'ambiente gia installato.
uv run --no-sync python sync_intranet.py
if errorlevel 1 goto intranet_failure
goto sync_complete
:skip_intranet
echo Pubblicazione intranet saltata: disponibile solo dal ramo main.
:sync_complete
echo.
echo %SYNC_ESC%[96mSincronizzazione completata.%SYNC_ESC%[0m
exit /b 0

:check_ok
echo Prerequisiti verificati. Ramo: %SYNC_BRANCH%.
git status --short
exit /b 0

:usage_error
echo Uso: sync.bat oppure sync.bat --check
goto failure
:missing_git
echo Git non disponibile. Installare Git e riaprire il terminale.
goto failure
:missing_uv
echo uv non disponibile. Installare uv e preparare l'ambiente con uv sync.
goto failure
:intranet_failure
echo GitHub sincronizzato; pubblicazione intranet non completata.
echo Controllare rete e permessi, poi rilanciare sync.bat.
exit /b 1
:missing_repository
echo Questa cartella non contiene un repository Git.
goto failure
:missing_origin
echo Il repository non ha un remoto origin configurato.
goto failure
:detached_head
echo Nessun ramo attivo. Selezionare un ramo prima di sincronizzare.
goto failure
:unfinished_operation
echo Esiste un'operazione Git incompleta. Controllare git status e completarla prima di sincronizzare.
goto failure
:merge_failure
echo Integrazione non completata. Controllare git status e risolvere eventuali conflitti.
echo Dopo la risoluzione, usare git add e git commit prima di rilanciare sync.bat.
goto failure
:failure
echo.
echo Sincronizzazione interrotta. Le modifiche locali restano disponibili.
echo Controllare i messaggi precedenti; se richiesto, completare l'accesso a GitHub.
exit /b 1
