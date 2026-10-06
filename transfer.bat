@echo off
setlocal
title TRASFERIMENTO STRUMENTI - LIS
chcp 65001 > nul
pushd "%~dp0"
if errorlevel 1 exit /b 1
set "UV_CACHE_DIR=%~dp0.uv-cache"
echo =======================================================
echo          TRASFERIMENTO STRUMENTI - LIS
echo =======================================================
uv run --locked python trasfer.py
if errorlevel 1 (
    echo Impossibile avviare il trasferimento. Verificare che uv sia disponibile.
    popd
    pause
    exit /b 1
)
popd
exit /b 0
