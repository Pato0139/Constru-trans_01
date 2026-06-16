@echo off
chcp 65001 >nul
echo ================================================================
echo   CONSTRU-TRANS - Setup automatico
echo ================================================================
echo.
echo Ejecutando script de PowerShell...
echo.

powershell -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"

pause

