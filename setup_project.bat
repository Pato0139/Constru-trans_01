@echo off
setlocal enabledelayedexpansion

:: Asegurar que el script corra en la carpeta donde esta ubicado
cd /d "%~dp0"

echo ===================================================
echo   ConstruTrans - Script de Inicializacion Pro
echo ===================================================

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo Por favor descargalo de python.org e intentalo de nuevo.
    pause
    exit /b
)

:: 2. Configurar .env
if not exist ".env" (
    echo [1/5] Configurando entorno (.env)...
    if exist ".env.example" (
        copy .env.example .env >nul
        echo [OK] .env creado desde .env.example
    ) else (
        echo SECRET_KEY=django-insecure-!%random%!%random% > .env
        echo DEBUG=True >> .env
        echo ALLOWED_HOSTS=127.0.0.1,localhost >> .env
        echo [OK] .env basico generado
    )
)

:: 3. Crear y Activar VENV
if not exist "venv" (
    echo [2/5] Creando entorno virtual (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo crear el entorno virtual.
        pause
        exit /b
    )
)

echo [3/5] Instalando dependencias (esto puede tardar)...
:: Usar la ruta completa al python del venv para instalar pip y requirements
venv\Scripts\python.exe -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo [ALERTA] No se pudo actualizar pip, continuando con la version actual...
)

venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Fallo la instalacion de dependencias. 
    echo Revisa tu conexion a internet o si el archivo requirements.txt es valido.
    pause
    exit /b
)
echo [OK] Dependencias instaladas correctamente.

:: 4. Base de Datos
echo [4/5] Aplicando migraciones locales...
venv\Scripts\python.exe manage.py migrate --no-input
if %errorlevel% neq 0 (
    echo [ERROR] Fallaron las migraciones.
    pause
    exit /b
)

:: 5. Cargar Datos o Crear Superusuario
if exist "db_backup.json" (
    echo [5/5] Cargando base de datos de respaldo...
    venv\Scripts\python.exe manage.py loaddata db_backup.json
    if %errorlevel% neq 0 (
        echo [ALERTA] No se pudieron cargar algunos datos del respaldo.
    )
) else (
    echo [5/5] No hay respaldo. Crea un administrador:
    venv\Scripts\python.exe manage.py createsuperuser
)

echo.
echo ===================================================
echo   TODO LISTO! Proyecto configurado correctamente.
echo ===================================================
echo.
echo Para entrar al sistema:
echo 1. Ejecuta: python manage.py runserver (con el venv activado)
echo 2. Abre: http://127.0.0.1:8000
echo.
set /p run="Deseas iniciar el servidor ahora? (s/n): "
if /i "%run%"=="s" (
    venv\Scripts\python.exe manage.py runserver
)
echo.
echo Para trabajar en el proyecto, recuerda activar el venv con:
echo .\venv\Scripts\activate
echo.
pause
