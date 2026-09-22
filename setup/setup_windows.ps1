
Write-Host "================================================================" -ForegroundColor cyan
Write-Host "  CONSTRU-TRANS - Setup automatico (Windows)" -ForegroundColor blue
Write-Host "================================================================" -ForegroundColor cyan
Write-Host "==Derechos_Autor==Edward_Fonseca==_-_==" -ForegroundColor black
Write-Host "Iniciando..." -ForegroundColor Green
Write-Host ""

# Cambiar al directorio raíz del proyecto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Paso 1: Verificar Python
Write-Host "[1/5] Verificando Python..." -ForegroundColor blue
$pythonCmd = $null
$pyArgs = @()
$pythonVersion = ""

# Intentar encontrar Python a traves del lanzador 'py' prefiriendo 3.12, 3.11, 3.13, 3.14
try {
    $null = Get-Command py -ErrorAction Stop
    $preferredVersions = @("-3.12", "-3.11", "-3.13", "-3.14")
    foreach ($ver in $preferredVersions) {
        $testOutput = & py $ver --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $testOutput -match "Python\s+3\.") {
            $pythonCmd = "py"
            $pyArgs = @($ver)
            $pythonVersion = $testOutput.Trim()
            break
        }
    }
    if (-not $pythonCmd) {
        $testOutput = & py --version 2>&1
        if ($testOutput -match "Python\s+3\.") {
            $pythonCmd = "py"
            $pythonVersion = $testOutput.Trim()
        }
    }
} catch {}

if (-not $pythonCmd) {
    try {
        $testOutput = & python --version 2>&1
        if ($testOutput -match "Python\s+3\.") {
            $pythonCmd = "python"
            $pythonVersion = $testOutput.Trim()
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host ""
    Write-Host "[ERROR] Python no encontrado. Instala Python 3.11 o superior (recomendado 3.12)." -ForegroundColor Red
    Write-Host "Descarga: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}

Write-Host "[OK] Python seleccionado: $pythonVersion" -ForegroundColor Green

# Paso 2: Crear entorno virtual
Write-Host ""
Write-Host "[2/5] Creando entorno virtual..." -ForegroundColor blue
if (Test-Path "venv") {
    # Verificar si el venv existente esta roto o incompleto
    if (-not (Test-Path "venv\Scripts\python.exe") -or -not (Test-Path "venv\Scripts\activate.bat")) {
        Write-Host "[AVISO] Entorno virtual anterior corrupto o incompleto. Recreando..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force "venv"
    }
}

if (-not (Test-Path "venv")) {
    if ($pyArgs.Count -gt 0) {
        & $pythonCmd $pyArgs -m venv venv
    } else {
        & $pythonCmd -m venv venv
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo al crear entorno virtual." -ForegroundColor Red
        Read-Host "Presiona cualquier tecla para salir"
        exit 1
    }
    Write-Host "[OK] Entorno virtual creado exitosamente" -ForegroundColor Green
} else {
    Write-Host "[OK] Entorno virtual existente verificado" -ForegroundColor Green
}

# Paso 3: Instalar dependencias
Write-Host ""
Write-Host "[3/5] Instalando dependencias..." -ForegroundColor blue
& .\venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al actualizar pip" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}

# Usar --prefer-binary para priorizar ruedas precompiladas y evitar fallos por compilacion en Windows
& .\venv\Scripts\python.exe -m pip install --prefer-binary -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al instalar dependencias." -ForegroundColor Red
    Write-Host "Asegurate de que las versiones en requirements.txt cuenten con ruedas (wheels) precompiladas." -ForegroundColor Yellow
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green

# Paso 4: Configurar .env local
Write-Host ""
Write-Host "[4/5] Configurando archivo .env local..." -ForegroundColor blue
Write-Host ""
Write-Host "================================================================" -ForegroundColor cyan
Write-Host "  OBTENIENDO CREDENCIALES AUTOMATICAMENTE" -ForegroundColor blue
Write-Host "================================================================" -ForegroundColor cyan
Write-Host ""

$neonRepoUrl = "https://github.com/Pato0139/Neon.git"
$tempDir = "temp_neon_repo"
$envCreado = $false

try {
    Write-Host "[1/3] Clonando repositorio de credenciales..." -ForegroundColor blue
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir
    }
    git clone --depth 1 $neonRepoUrl $tempDir
    if ($LASTEXITCODE -ne 0) {
        throw "git clone fallo con codigo de salida $LASTEXITCODE"
    }
    Write-Host "[OK] Repositorio clonado" -ForegroundColor Green

    Write-Host "[2/3] Copiando archivo de configuración..." -ForegroundColor blue
    $neonEnvPath = Join-Path $tempDir ".env.example"
    if (Test-Path $neonEnvPath) {
        Copy-Item -Path $neonEnvPath -Destination ".env" -Force
        Write-Host "[OK] Archivo .env creado con todas las credenciales!" -ForegroundColor Green
        $envCreado = $true
    } else {
        Write-Host "[AVISO] No se encontró .env.example en el repo" -ForegroundColor Yellow
    }

    Write-Host "[3/3] Limpiando repositorio temporal..." -ForegroundColor blue
    Remove-Item -Recurse -Force $tempDir
    Write-Host "[OK] Repositorio temporal eliminado" -ForegroundColor Green
} catch {
    Write-Host "[AVISO] No se pudo obtener el repositorio de credenciales: $($_.Exception.Message)" -ForegroundColor Yellow
    if (Test-Path $tempDir) {
        Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    }
}

# Si no se pudo crear desde el repo, creamos uno básico
if (-not $envCreado) {
    Write-Host ""
    Write-Host "[OK] Generando configuración básica..." -ForegroundColor blue
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
Write-Host "[5/5] Aplicando migraciones..." -ForegroundColor blue
& .\venv\Scripts\python.exe manage.py migrate --run-syncdb
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Las migraciones locales fallaron. El setup no puede continuar." -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] Migraciones aplicadas en base local" -ForegroundColor Green

$applyRemoteMigrations = if ($env:APPLY_REMOTE_MIGRATIONS) {
    $env:APPLY_REMOTE_MIGRATIONS.ToLowerInvariant() -eq "true"
} else {
    $true
}

if ($databaseUrl -and $applyRemoteMigrations) {
    Write-Host ""
    Write-Host "[INFO] Aplicando migraciones en base remota..." -ForegroundColor Yellow
    & .\venv\Scripts\python.exe manage.py migrate --database=remota
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Las migraciones remotas fallaron. No se marcaran como completadas." -ForegroundColor Red
        Read-Host "Presiona cualquier tecla para salir"
        exit 1
    }
    Write-Host "[OK] Migraciones aplicadas en base remota" -ForegroundColor Green
} elseif ($databaseUrl) {
    Write-Host "[AVISO] DATABASE_URL esta configurada, pero las migraciones remotas estan desactivadas." -ForegroundColor Yellow
    Write-Host "[INFO] Para ejecutarlas explicitamente: `$env:APPLY_REMOTE_MIGRATIONS='true'; .\setup\setup_windows.ps1" -ForegroundColor Yellow
}

# Final
Write-Host ""
Write-Host "================================================================" -ForegroundColor cyan
Write-Host "  Setup COMPLETO!" -ForegroundColor blue
Write-Host "================================================================" -ForegroundColor cyan
Write-Host ""
Write-Host "Para iniciar el servidor:" -ForegroundColor blue
Write-Host "  .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor cyan
Read-Host "Presiona cualquier tecla para salir"

