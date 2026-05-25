
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CONSTRU-TRANS - Setup automatico (Windows)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio raíz del proyecto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Paso 1: Verificar Python
Write-Host "[1/8] Verificando Python..." -ForegroundColor Yellow
$pythonCmd = $null

try {
    $pyCmd = Get-Command py -ErrorAction Stop
    $pythonVersion = & py --version 2>&1
    if ($pythonVersion -match "Python") {
        Write-Host "[OK] Python encontrado (py): $pythonVersion" -ForegroundColor Green
        $pythonCmd = "py"
    }
} catch {}

if (-not $pythonCmd) {
    try {
        $pythonVersion = & python --version 2>&1
        if ($pythonVersion -match "Python") {
            Write-Host "[OK] Python encontrado: $pythonVersion" -ForegroundColor Green
            $pythonCmd = "python"
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host ""
    Write-Host "[ERROR] Python no encontrado. Instala Python 3.11+" -ForegroundColor Red
    Write-Host "Descarga: https://www.python.org/downloads/" -ForegroundColor White
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}

# Paso 2: Crear entorno virtual
Write-Host ""
Write-Host "[2/8] Creando entorno virtual..." -ForegroundColor Yellow
if (-not (Test-Path "venv")) {
    & $pythonCmd -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo al crear entorno virtual" -ForegroundColor Red
        Read-Host "Presiona cualquier tecla para salir"
        exit 1
    }
    Write-Host "[OK] Entorno virtual creado" -ForegroundColor Green
} else {
    Write-Host "[OK] Entorno virtual ya existe" -ForegroundColor Green
}

# Paso 3: Instalar dependencias
Write-Host ""
Write-Host "[3/8] Instalando dependencias..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al actualizar pip" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
& .\venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al instalar dependencias" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green

# Paso 4: Configurar .env local
Write-Host ""
Write-Host "[4/8] Configurando archivo .env local..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env" -Force
        Write-Host "[OK] Archivo .env creado desde .env.example" -ForegroundColor Green
    } else {
        @"
DJANGO_ENV=development
SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
DATABASE_URL=
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=Constru-Trans <no-reply@example.com>
SERVER_EMAIL=Constru-Trans <no-reply@example.com>
USE_S3=False
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-Host "[OK] Archivo .env creado con valores minimos" -ForegroundColor Green
    }
    
    # Generar SECRET_KEY aleatorio
    $secretKey = & .\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    (Get-Content .env) -replace 'SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres', "SECRET_KEY=$secretKey" | Set-Content .env
    Write-Host "[OK] SECRET_KEY generado" -ForegroundColor Green
} else {
    Write-Host "[OK] Archivo .env ya existe" -ForegroundColor Green
}

# Paso 5: Aplicar migraciones
Write-Host ""
Write-Host "[5/8] Aplicando migraciones..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py migrate --run-syncdb
if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] Verificando configuracion..." -ForegroundColor Yellow
    & .\venv\Scripts\python.exe manage.py check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Problema con la configuracion" -ForegroundColor Red
    } else {
        Write-Host "[OK] Configuracion verificada" -ForegroundColor Green
    }
} else {
    Write-Host "[OK] Migraciones aplicadas" -ForegroundColor Green
}

# Paso 6: Crear superusuario si no existe
Write-Host ""
Write-Host "[6/8] Creando superusuario si no existe..." -ForegroundColor Yellow
$resultado = & .\venv\Scripts\python.exe manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('[OK] Superusuario creado')
else:
    print('[OK] Superusuario ya existe')
" 2>&1
Write-Host $resultado -ForegroundColor Green

# Paso 7: Recolectar archivos estaticos
Write-Host ""
Write-Host "[7/8] Recolectando archivos estaticos..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py collectstatic --noinput 2>$null
Write-Host "[OK] Archivos estaticos recolectados" -ForegroundColor Green

# Paso 8: Cargar datos de prueba (opcional)
Write-Host ""
Write-Host "[8/8] Cargando datos de prueba (opcional)..." -ForegroundColor Yellow
if (Test-Path "scripts\seed_data.py") {
    & .\venv\Scripts\python.exe scripts/seed_data.py
    Write-Host "[OK] Datos de prueba cargados" -ForegroundColor Green
} else {
    Write-Host "[OK] No hay script de datos opcional" -ForegroundColor Green
}

# Verificar si usa BD remota
$dbUrl = ""
if (Test-Path ".env") {
    $dbUrl = Select-String -Path ".env" -Pattern "^DATABASE_URL=" | ForEach-Object { $_.Line.Split("=")[1] }
}

# Final
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup COMPLETO!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el servidor:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor White
Write-Host ""
if ($dbUrl) {
    Write-Host "[INFO] Usando base de datos Neon PostgreSQL" -ForegroundColor Gray
} else {
    Write-Host "[INFO] Usando base de datos SQLite local (offline)" -ForegroundColor Gray
}
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Read-Host "Presiona cualquier tecla para salir"
