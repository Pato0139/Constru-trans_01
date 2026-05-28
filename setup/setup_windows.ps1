
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CONSTRU-TRANS - Setup automatico (Windows)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio raíz del proyecto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Paso 1: Verificar Python
Write-Host "[1/5] Verificando Python..." -ForegroundColor Yellow
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
Write-Host "[2/5] Creando entorno virtual..." -ForegroundColor Yellow
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
Write-Host "[3/5] Instalando dependencias..." -ForegroundColor Yellow
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
Write-Host "[4/5] Configurando archivo .env local..." -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================================" -ForegroundColor Magenta
Write-Host "  OBTENIENDO CREDENCIALES AUTOMATICAMENTE" -ForegroundColor Magenta
Write-Host "================================================================" -ForegroundColor Magenta
Write-Host ""

$neonRepoUrl = "https://github.com/Pato0139/Neon.git"
$tempDir = "temp_neon_repo"
$envCreado = $false

try {
    Write-Host "[1/3] Clonando repositorio de credenciales..." -ForegroundColor Cyan
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
    git clone --depth 1 $neonRepoUrl $tempDir 2>&1 | Out-Null
    Write-Host "[OK] Repositorio clonado" -ForegroundColor Green

    Write-Host "[2/3] Copiando archivo de configuración..." -ForegroundColor Cyan
    $neonEnvPath = Join-Path $tempDir ".env.example"
    if (Test-Path $neonEnvPath) {
        Copy-Item -Path $neonEnvPath -Destination ".env" -Force
        Write-Host "[OK] Archivo .env creado con todas las credenciales!" -ForegroundColor Green
        $envCreado = $true
    } else {
        Write-Host "[AVISO] No se encontró .env.example en el repo" -ForegroundColor Yellow
    }

    Write-Host "[3/3] Limpiando repositorio temporal..." -ForegroundColor Cyan
    Remove-Item -Recurse -Force $tempDir
    Write-Host "[OK] Repositorio temporal eliminado" -ForegroundColor Green
} catch {
    Write-Host "[AVISO] No se pudo clonar el repositorio" -ForegroundColor Yellow
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    }
}

# Si no se pudo crear desde el repo, creamos uno básico
if (-not $envCreado) {
    Write-Host ""
    Write-Host "[OK] Generando configuración básica..." -ForegroundColor Cyan
    $djangoEnv = "development"
    $secretKey = & .\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    
    $envContent = @"
# Variables minimas para desarrollo local
DJANGO_ENV=$djangoEnv
SECRET_KEY=$secretKey
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# Base de datos local por defecto (SQLite)
DATABASE_URL=

# Email en desarrollo
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=Constru-Trans <no-reply@example.com>
SERVER_EMAIL=Constru-Trans <no-reply@example.com>

# Almacenamiento opcional en S3
USE_S3=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_ENDPOINT_URL=
AWS_S3_REGION_NAME=us-east-1
"@

    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "[OK] Archivo .env creado con valores básicos" -ForegroundColor Green
}

# Verificamos si tenemos DATABASE_URL
$databaseUrl = ""
if (Test-Path ".env") {
    $match = Select-String -Path ".env" -Pattern "^DATABASE_URL=(.*)$"
    if ($match) {
        $databaseUrl = $match.Matches[0].Groups[1].Value.Trim()
    }
}

Write-Host ""
if ($databaseUrl) {
    Write-Host "[OK] DATABASE_URL configurada! Modo híbrido activado (SQLite local + Neon remota)" -ForegroundColor Green
} else {
    Write-Host "[INFO] Usando solo base de datos SQLite local (modo offline)" -ForegroundColor Gray
}

# Paso 5: Aplicar migraciones
Write-Host ""
Write-Host "[5/5] Aplicando migraciones..." -ForegroundColor Yellow
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

# Final
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup COMPLETO!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el servidor:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Read-Host "Presiona cualquier tecla para salir"

