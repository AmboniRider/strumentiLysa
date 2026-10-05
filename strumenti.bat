@echo off
title STRUMENTI DI LABORATORIO - LIS
chcp 65001 > nul
cd /d "%~dp0"

echo =======================================================
echo          STRUMENTI DI LABORATORIO - LIS
echo =======================================================
echo.
echo Avvio dell'applicazione in corso...
echo.

uv run python app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Si e' verificato un errore durante l'esecuzione del programma.
    echo Codice di uscita: %ERRORLEVEL%
    pause
)
