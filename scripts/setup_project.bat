@echo off
setlocal

:: Asegurar que el script corra en la carpeta raiz del proyecto
cd /d "%~dp0\.."

echo ===================================================
echo   ConstruTrans - Script para Inicializar ConstruTrans
echo   Sincronizacion Final: %date% %time%
echo ===================================================

:: 1. Verificar Python
echo [1/5] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 goto :CHECK_PY
set "PYTHON_CMD=python"
goto :PYTHON_OK

:CHECK_PY
py --version >nul 2>&1
if errorlevel 1 goto :PYTHON_ERROR
set "PYTHON_CMD=py"
goto :PYTHON_OK

:PYTHON_ERROR
echo [ERROR] No se encontro Python ni el lanzador 'py'.
echo Por favor instala Python desde https://www.python.org/
pause
exit /b

:PYTHON_OK
echo [OK] Usando: %PYTHON_CMD%

:: 2. Configurar .env
if exist ".env" goto :VENV_CHECK
echo [2/5] Configurando entorno (.env)...
if not exist ".env.example" goto :CREATE_ENV
copy .env.example .env >nul
echo [OK] .env creado desde .env.example
goto :VENV_CHECK

:CREATE_ENV
echo SECRET_KEY=django-insecure-generic-key-12345 > .env
echo DEBUG=True >> .env
echo ALLOWED_HOSTS=127.0.0.1,localhost >> .env
echo [OK] .env basico generado

:VENV_CHECK
:: 3. Crear y Activar VENV
if exist "venv" goto :INSTALL_DEPS
echo [3/5] Creando entorno virtual (venv)...
%PYTHON_CMD% -m venv venv
if errorlevel 1 goto :VENV_ERROR
goto :INSTALL_DEPS

:VENV_ERROR
echo [ERROR] No se pudo crear el entorno virtual.
pause
exit /b

:INSTALL_DEPS
echo [4/5] Instalando dependencias (esto puede tardar)...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :DEPS_ERROR
echo [OK] Dependencias instaladas correctamente.
goto :MIGRATIONS

:DEPS_ERROR
echo [ERROR] Fallo la instalacion de dependencias.
pause
exit /b

:MIGRATIONS
:: 4. Base de Datos
echo [5/5] Aplicando migraciones locales...
venv\Scripts\python.exe manage.py migrate --no-input
if errorlevel 1 goto :MIGRATE_ERROR
goto :DONE

:MIGRATE_ERROR
echo [ERROR] Fallaron las migraciones.
pause
exit /b

:DONE
echo.
echo ===================================================
echo   TODO LISTO! Proyecto configurado correctamente.
echo ===================================================
echo.
echo Para entrar al sistema:
echo 1. Ejecuta: python manage.py runserver
echo 2. Abre: http://127.0.0.1:8000
echo.
pause
