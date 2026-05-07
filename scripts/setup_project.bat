
@echo off
setlocal

:: Asegurar que el script corra en la carpeta raiz del proyecto
cd /d "%~dp0\.."

echo ===================================================
echo   ConstruTrans - Script de Configuracion
echo   Fecha: %date% %time%
echo ===================================================
echo.

:: 1. Verificar Python
echo [Paso 1/6] Verificando Python...
python --version >nul 2>&amp;1
if errorlevel 1 goto :CHECK_PY
set "PYTHON_CMD=python"
goto :PYTHON_OK

:CHECK_PY
py --version &gt;nul 2&gt;&amp;1
if errorlevel 1 goto :PYTHON_ERROR
set "PYTHON_CMD=py"
goto :PYTHON_OK

:PYTHON_ERROR
echo [ERROR] No se encontro Python ni el lanzador 'py'.
echo Por favor instala Python desde https://www.python.org/
echo.
pause
exit /b

:PYTHON_OK
echo [OK] Usando: %PYTHON_CMD%
echo.

:: 2. Configurar .env
if exist ".env" goto :VENV_CHECK
echo [Paso 2/6] Configurando entorno (.env)...
if not exist ".env.example" goto :CREATE_ENV
copy .env.example .env &gt;nul
echo [OK] .env creado desde .env.example
goto :VENV_CHECK

:CREATE_ENV
echo SECRET_KEY=django-insecure-generic-key-12345 &gt; .env
echo DEBUG=True &gt;&gt; .env
echo ALLOWED_HOSTS=127.0.0.1,localhost &gt;&gt; .env
echo [OK] .env basico generado
goto :VENV_CHECK

:VENV_CHECK
:: 3. Crear y Activar VENV
if exist "venv" goto :INSTALL_DEPS
echo [Paso 3/6] Creando entorno virtual (venv)...
%PYTHON_CMD% -m venv venv
if errorlevel 1 goto :VENV_ERROR
echo [OK] Entorno virtual creado
echo.
goto :INSTALL_DEPS

:VENV_ERROR
echo [ERROR] No se pudo crear el entorno virtual.
echo.
pause
exit /b

:INSTALL_DEPS
echo [Paso 4/6] Instalando dependencias (esto puede tardar)...
echo.
venv\Scripts\python.exe -m pip install --upgrade pip
echo.
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :DEPS_ERROR
echo.
echo [OK] Dependencias instaladas correctamente.
echo.
goto :MIGRATIONS

:DEPS_ERROR
echo [ERROR] Fallo la instalacion de dependencias.
echo.
pause
exit /b

:MIGRATIONS
:: 4. Aplicar migraciones
echo [Paso 5/6] Aplicando migraciones...
venv\Scripts\python.exe manage.py migrate --no-input
if errorlevel 1 goto :MIGRATE_ERROR
echo [OK] Migraciones aplicadas correctamente
echo.
goto :COLLECT_STATIC

:MIGRATE_ERROR
echo [ERROR] Fallaron las migraciones.
echo.
pause
exit /b

:COLLECT_STATIC
:: 5. Recolectar archivos estaticos (si es necesario)
echo [Paso 6/6] Preparando archivos estaticos...
echo [OK] Archivos listos
echo.
goto :DONE

:DONE
echo ===================================================
echo   TODO LISTO! Proyecto configurado correctamente.
echo ===================================================
echo.
echo Para iniciar el servidor:
echo   1. Ejecuta: scripts\iniciar.bat
echo   O manualmente:
echo   1. Activa el entorno: venv\Scripts\activate.bat
echo   2. Ejecuta: python manage.py runserver
echo.
echo Luego abre tu navegador en: http://127.0.0.1:8000
echo.
pause
