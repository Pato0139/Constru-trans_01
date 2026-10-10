@echo off
chcp 65001 >nul
set "TEMP_DIR=%~dp0temp_neon_repo"
powershell -ExecutionPolicy Bypass -File "%~dp0setup\setup_windows.ps1"
if exist "%TEMP_DIR%" (rmdir /s /q "%TEMP_DIR%" >nul 2>&1)
pause
