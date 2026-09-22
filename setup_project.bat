@echo off
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -File "%~dp0setup\setup_windows.ps1"
pause
