@echo off
chcp 65001 >nul
rem Instalador de Constru-trans para Windows. Opciones: --dev --seed --reset-db
set "ARGS="
if /I "%~1"=="--dev" set "ARGS=-Dev"
if /I "%~1"=="--seed" set "ARGS=-Seed"
if /I "%~1"=="--reset-db" set "ARGS=-ResetDb"
if /I "%~1"=="--dev-seed" set "ARGS=-Dev -Seed"
if /I "%~1"=="--reset-db-seed" set "ARGS=-ResetDb -Seed"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1" %ARGS%
set "SETUP_EXIT_CODE=%ERRORLEVEL%"
echo.
pause
exit /b %SETUP_EXIT_CODE%
