@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ================================================================
echo   CONSTRU-TRANS - Setup automatico
echo ================================================================
echo.

REM ---- 1. Encontrar Python ----
set PYTHON_CMD=
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto :python_found
)

python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto :python_found
)

echo [ERROR] Python no encontrado. Instala Python 3.11+ desde python.org
echo Asegurate de marcar "Add Python to PATH" durante la instalacion.
pause
exit /b 1

:python_found
echo [OK] Python encontrado:
%PYTHON_CMD% --version

REM ---- 2. Crear entorno virtual ----
echo.
echo [1/4] Creando entorno virtual...
if not exist "venv\" (
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Fallo al crear entorno virtual
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
) else (
    echo [OK] Entorno virtual ya existe
)

REM ---- 3. Instalar dependencias en el venv ----
echo.
echo [2/4] Instalando dependencias (puede tardar)...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo al instalar dependencias
    pause
    exit /b 1
)
echo [OK] Dependencias instaladas

REM ---- 4. Verificar .env ----
echo.
echo [3/4] Verificando archivo .env...
if not exist ".env" (
    copy .env.example .env >nul
    echo [OK] Archivo .env creado
) else (
    echo [OK] Archivo .env ya existe
)

REM ---- 5. Aplicar migraciones ----
echo.
echo [4/4] Aplicando migraciones...
venv\Scripts\python.exe manage.py migrate
if errorlevel 1 (
    echo [ERROR] Fallo al aplicar migraciones
    pause
    exit /b 1
)
echo [OK] Migraciones aplicadas

echo.
echo ================================================================
echo   Setup COMPLETO!
echo ================================================================
echo.
echo Para iniciar el servidor:
echo   venv\Scripts\activate ^&^& python manage.py runserver
echo.
echo O directamente:
echo   venv\Scripts\python.exe manage.py runserver
echo.
pause
endlocal
