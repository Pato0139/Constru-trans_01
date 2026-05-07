
@echo off
setlocal

:: Asegurar que el script corra en la carpeta raiz del proyecto
cd /d "%~dp0\.."

echo ===================================================
echo   Iniciando Constru-Trans
echo ===================================================
echo.

:: Verificar que exista el entorno virtual
if not exist "venv" (
    echo [ERROR] No se encontro el entorno virtual 'venv'
    echo Por favor ejecuta primero: scripts\setup_project.bat
    echo.
    pause
    exit /b
)

:: Activar entorno virtual y ejecutar el servidor
call venv\Scripts\activate.bat

echo.
echo [OK] Entorno virtual activado
echo.
echo Iniciando servidor Django...
echo Abrir navegador en: http://127.0.0.1:8000
echo.
echo ===================================================
echo   Presiona Ctrl+C para detener el servidor
echo ===================================================
echo.

python manage.py runserver

echo.
echo Servidor detenido.
pause
