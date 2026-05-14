@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ================================================================
echo   CONSTRU-TRANS - Setup automatico (modo hibrido local + Neon)
echo ================================================================
echo.

REM ---- 1. Verificar Python ----
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.11+ desde python.org
    pause & exit /b 1
)
python --version

REM ---- 2. Crear entorno virtual ----
if not exist "venv\" (
    echo [1/6] Creando entorno virtual...
    python -m venv venv
) else (
    echo [1/6] Entorno virtual ya existe.
)

REM ---- 3. Activar venv ----
echo [2/6] Activando entorno virtual...
call venv\Scripts\activate.bat

REM ---- 4. Instalar dependencias ----
echo [3/6] Instalando dependencias (puede tardar 2-5 min)...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] Fallo pip install & pause & exit /b 1 )

REM ---- 5. Verificar .env ----
if not exist ".env" (
    echo [4/6] No existe .env. Intentando descargar desde repositorio privado...
    echo.
    where git >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Git no encontrado. Copiando desde .env.example...
        copy .env.example .env >nul
    ) else (
        powershell -ExecutionPolicy Bypass -File scripts\download_env.ps1
        if errorlevel 1 (
            echo [ADVERTENCIA] No se pudo descargar .env. Copiando desde .env.example...
            copy .env.example .env >nul
        )
    )
    if not exist ".env" (
        echo [ERROR] No se pudo crear .env. Saliendo...
        pause & exit /b 1
    )
) else (
    echo [4/6] .env ya existe.
)

REM ---- 6. Aplicar migraciones (las migraciones YA estan versionadas) ----
echo [5/6] Aplicando migraciones a la BD local (SQLite)...
python manage.py migrate
if errorlevel 1 ( echo [ERROR] Fallaron migraciones & pause & exit /b 1 )

REM ---- 7. Seed inicial (idempotente) ----
echo        Cargando datos iniciales (roles, metodos de pago)...
python manage.py seed_mer

REM ---- 8. Cargar backup si existe (opcional) ----
if exist "db_backup.json" (
    echo        Cargando db_backup.json...
    python manage.py loaddata db_backup.json
)

REM ---- 9. Collectstatic ----
echo [6/6] Recolectando archivos estaticos...
python manage.py collectstatic --noinput >nul 2>&1

REM ---- 10. Superusuario opcional ----
echo.
set /p crear_admin="Crear superusuario ahora? (s/n): "
if /i "!crear_admin!"=="s" ( python manage.py createsuperuser )

echo.
echo ================================================================
echo   Setup COMPLETO.
echo   - BD local (SQLite): db.sqlite3 (funciona offline)
echo   - BD remota (Neon): se usa si DATABASE_URL esta configurada
echo ================================================================
echo.
set /p iniciar="Iniciar servidor ahora? (s/n): "
if /i "!iniciar!"=="s" (
    python manage.py runserver
) else (
    echo Para iniciar manualmente:
    echo   venv\Scripts\activate ^&^& python manage.py runserver
)

pause
endlocal
