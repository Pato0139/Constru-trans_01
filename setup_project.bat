@echo off
setlocal enabledelayedexpansion

echo ===================================================
echo   ConstruTrans - Script de Inicializacion Pro
echo ===================================================

:: 1. Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no esta instalado. Descargalo de python.org
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
)
echo [3/5] Instalando dependencias (esto puede tardar)...
call venv\Scripts\activate
python -m pip install --upgrade pip >nul
pip install -r requirements.txt --force-reinstall

:: 4. Base de Datos
echo [4/5] Aplicando migraciones locales...
python manage.py migrate --no-input

:: 5. Cargar Datos o Crear Superusuario
if exist "db_backup.json" (
    echo [5/5] Cargando base de datos de respaldo...
    python manage.py loaddata db_backup.json
) else (
    echo [5/5] No hay respaldo. Crea un administrador:
    python manage.py createsuperuser
)

echo.
echo ===================================================
echo   TODO LISTO! Proyecto configurado correctamente.
echo ===================================================
echo.
echo Para entrar al sistema:
echo 1. Ejecuta: python manage.py runserver
echo 2. Abre: http://127.0.0.1:8000
echo.
set /p run="Deseas iniciar el servidor ahora? (s/n): "
if /i "%run%"=="s" (
    python manage.py runserver
)
pause
