@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_windows.ps1"
set "SETUP_EXIT_CODE=%ERRORLEVEL%"
pause
exit /b %SETUP_EXIT_CODE%
