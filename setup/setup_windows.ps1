# ============================================================
#  CONSTRU-TRANS - Instalador para Windows (PowerShell)
#  Uso:  .\setup\setup_windows.ps1 [-Dev] [-Seed] [-ResetDb] [-NoFetchCredentials]
#  Por defecto intenta usar el repositorio compartido de credenciales,
#  igual que hacia el instalador original.
# ============================================================
param(
    [switch]$Dev,
    [switch]$Seed,
    [switch]$ResetDb,
    [switch]$NoFetchCredentials
)

$ErrorActionPreference = "Stop"

$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

function Write-Ok    { param([string]$m) Write-Host "[OK] $m" -ForegroundColor Green }
function Write-Warn  { param([string]$m) Write-Host "[AVISO] $m" -ForegroundColor Yellow }
function Write-Err   { param([string]$m) Write-Host "[ERROR] $m" -ForegroundColor Red }
function Write-Step  { param([string]$m) Write-Host ""; Write-Host $m -ForegroundColor Cyan }

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "CONSTRU-TRANS - Instalacion automatica (Windows)" -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Cyan

# ---------- [1/6] Python ----------
Write-Step "[1/6] Verificando Python..."

function Test-PythonVenv {
    param([string]$PythonPath)
    if (-not $PythonPath) { return $null }
    if (-not (Test-Path $PythonPath -PathType Leaf)) { return $null }
    $probe = "import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 11) and sys.prefix != sys.base_prefix else 1)"
    try {
        $out = & $PythonPath -c $probe 2>&1
        if ($LASTEXITCODE -eq 0) { return ($out | Select-Object -Last 1).ToString().Trim() }
    } catch { return $null }
    return $null
}

function Test-PythonBase {
    param([string]$Command, [string[]]$Arguments)
    $probe = "import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    try {
        $all = @($Arguments) + @("-c", $probe)
        $out = & $Command @all 2>&1
        if ($LASTEXITCODE -eq 0) { return ($out | Select-Object -Last 1).ToString().Trim() }
    } catch { return $null }
    return $null
}

$venvPath = $null
$venvPython = $null
$pythonVersion = $null
$prefix = $projectRoot.TrimEnd("\") + "\"

# 1) Entorno virtual ya activado dentro del proyecto
if ($env:VIRTUAL_ENV) {
    $activo = [System.IO.Path]::GetFullPath($env:VIRTUAL_ENV).TrimEnd("\")
    if ($activo.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        $cand = Join-Path $activo "Scripts\python.exe"
        $v = Test-PythonVenv $cand
        if ($v) { $venvPath = $activo; $venvPython = $cand; $pythonVersion = $v; Write-Ok "Se reutiliza el entorno activo: $venvPath" }
    }
}

# 2) Entornos existentes en la carpeta del proyecto
if (-not $venvPython) {
    $candidatos = @((Join-Path $projectRoot ".venv"), (Join-Path $projectRoot "venv"))
    $candidatos += Get-ChildItem -Path $projectRoot -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like ".venv-*" } | Sort-Object Name | ForEach-Object { $_.FullName }

    foreach ($c in $candidatos) {
        $v = Test-PythonVenv (Join-Path $c "Scripts\python.exe")
        if ($v) { $venvPath = $c; $venvPython = Join-Path $c "Scripts\python.exe"; $pythonVersion = $v; Write-Ok "Se reutiliza el entorno existente: $venvPath"; break }
    }
}

# 3) Crear uno nuevo
if (-not $venvPython) {
    $baseCmd = $null; $baseArgs = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($ver in @("-3.12", "-3.11", "-3.13", "-3.14")) {
            $v = Test-PythonBase "py" @($ver)
            if ($v) { $baseCmd = "py"; $baseArgs = @($ver); $pythonVersion = $v; break }
        }
    }
    if (-not $baseCmd -and (Get-Command python -ErrorAction SilentlyContinue)) {
        $v = Test-PythonBase "python" @()
        if ($v) { $baseCmd = "python"; $baseArgs = @(); $pythonVersion = $v }
    }
    if (-not $baseCmd) {
        Write-Err "No se encontro Python 3.11 o superior."
        Write-Warn "Instalalo desde https://www.python.org/downloads/ (marca 'Add python.exe to PATH') y vuelve a ejecutar el setup."
        exit 1
    }

    $venvPath = Join-Path $projectRoot ".venv"
    if (Test-Path $venvPath) {
        Write-Err "$venvPath existe pero no contiene un Python valido. No se borro nada."
        Write-Warn "Renombralo o eliminalo y vuelve a ejecutar el setup."
        exit 1
    }
    Write-Host "[INFO] Creando $venvPath con Python $pythonVersion ..." -ForegroundColor Gray
    & $baseCmd @baseArgs -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { Write-Err "No se pudo crear el entorno virtual."; exit 1 }
    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    if (-not (Test-PythonVenv $venvPython)) { Write-Err "El entorno recien creado no es valido."; exit 1 }
    Write-Ok "Entorno virtual creado"
}

# ---------- [2/6] Dependencias ----------
Write-Step "[2/6] Instalando dependencias..."
& $venvPython -m pip install --upgrade pip > $null
& $venvPython -m pip install --prefer-binary -r (Join-Path $projectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Err "Fallo la instalacion de dependencias. Revisa tu conexion a Internet."
    exit 1
}
Write-Ok "Dependencias instaladas"

if ($Dev) {
    Write-Host "[INFO] Instalando herramientas de desarrollo..." -ForegroundColor Gray
    & $venvPython -m pip install --prefer-binary -r (Join-Path $projectRoot "requirements\dev.txt")
    if ($LASTEXITCODE -ne 0) { Write-Warn "Fallaron las dependencias de desarrollo; el proyecto sigue operativo." }
}

# ---------- [3/6] .env ----------
Write-Step "[3/6] Configurando el archivo .env..."
$envPath = Join-Path $projectRoot ".env"

if (-not $NoFetchCredentials -and -not (Test-Path $envPath) -and (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "[INFO] Intentando obtener credenciales compartidas..." -ForegroundColor Gray
    $tempDir = Join-Path $projectRoot "temp_neon_repo"
    if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
    $env:GIT_TERMINAL_PROMPT = "0"
    & git clone --depth 1 https://github.com/Pato0139/Neon.git $tempDir 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        foreach ($nombre in @(".env", ".env.example")) {
            $origen = Join-Path $tempDir $nombre
            if (Test-Path $origen) { Copy-Item $origen $envPath -Force; Write-Ok ".env creado desde el repositorio de credenciales"; break }
        }
    } else {
        Write-Warn "No se pudo clonar (repo privado o sin acceso). Se usara la plantilla local."
    }
    if (Test-Path $tempDir) { Remove-Item $tempDir -Recurse -Force }
    Remove-Item Env:GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue
}

if (-not (Test-Path $envPath)) {
    $plantilla = Join-Path $projectRoot ".env.example"
    if (Test-Path $plantilla) { Copy-Item $plantilla $envPath -Force } else { New-Item -ItemType File -Path $envPath -Force | Out-Null }
    Write-Ok ".env creado desde .env.example"
} else {
    Write-Ok "Se conserva el .env existente"
}

# SECRET_KEY estable
$necesitaClave = $true
$contenido = Get-Content $envPath -ErrorAction SilentlyContinue
foreach ($linea in $contenido) {
    if ($linea -match '^\s*SECRET_KEY\s*=') {
        $valor = ($linea -split '=', 2)[1].Trim().Trim("'", '"')
        $malas = @("", "cambiar", "cambia-esto-por-una-clave-aleatoria-de-50-caracteres",
                   "change-me", "changeme", "secret-key", "example-secret-key")
        if ($valor.Length -ge 32 -and ($malas -notcontains $valor.ToLower())) { $necesitaClave = $false }
    }
}
if ($necesitaClave) {
    $nueva = (& $venvPython -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())").Trim()
    if (-not $nueva) { Write-Err "No se pudo generar SECRET_KEY."; exit 1 }
    $lineas = @(Get-Content $envPath -ErrorAction SilentlyContinue)
    $puesta = $false; $salida = @()
    foreach ($linea in $lineas) {
        if ($linea -match '^\s*SECRET_KEY\s*=') { $salida += "SECRET_KEY=$nueva"; $puesta = $true } else { $salida += $linea }
    }
    if (-not $puesta) { $salida += "SECRET_KEY=$nueva" }
    [System.IO.File]::WriteAllText($envPath, (($salida -join [Environment]::NewLine) + [Environment]::NewLine), [System.Text.UTF8Encoding]::new($false))
    Write-Ok "SECRET_KEY fija generada y guardada en .env"
} else {
    Write-Ok "SECRET_KEY valida encontrada en .env"
}

# ---------- [4/6] Base de datos ----------
Write-Step "[4/6] Preparando la base de datos local..."
$sqlite = Join-Path $projectRoot "db.sqlite3"
if ($ResetDb -and (Test-Path $sqlite)) {
    $respaldo = Join-Path $projectRoot ("db.sqlite3.broken-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
    Rename-Item $sqlite $respaldo
    Write-Warn "Base anterior apartada en: $(Split-Path -Leaf $respaldo)"
}

$envDatabaseUrlPrevio = $env:DATABASE_URL
try {
    $env:DATABASE_URL = ""

    Write-Host "[INFO] Verificando la configuracion de Django..." -ForegroundColor Gray
    & $venvPython manage.py check
    if ($LASTEXITCODE -ne 0) { Write-Err "La configuracion de Django no es valida."; exit 1 }
    Write-Ok "Configuracion correcta"

    Write-Host "[INFO] Aplicando migraciones..." -ForegroundColor Gray
    $salida = & $venvPython manage.py migrate --noinput 2>&1
    if ($LASTEXITCODE -ne 0) {
        $salida | Select-Object -Last 4 | ForEach-Object { Write-Host $_ -ForegroundColor Gray }
        if (($salida -join " ") -match "already exists") {
            Write-Warn "La base local quedo a medias entre dos versiones del esquema."
            Write-Warn "Solucion:  .\setup\setup_windows.ps1 -ResetDb"
            Write-Host "(No se borra nada: la base actual se aparta como db.sqlite3.broken-<fecha>)" -ForegroundColor Gray
        } else {
            Write-Err "Las migraciones de la base local fallaron."
        }
        $tieneRemota = ($contenido -match '^\s*DATABASE_URL=.+')
        if ($tieneRemota) {
            Write-Host "[INFO] Hay DATABASE_URL configurada: el proyecto usara la base compartida." -ForegroundColor Gray
        } elseif (Test-Path $sqlite) {
            Write-Warn "Ya existia una db.sqlite3: se conserva y el setup continua con ella."
        } else {
            Write-Err "No hay base utilizable. Revisa el error anterior o ejecuta con -ResetDb."
            exit 1
        }
    } else {
        Write-Ok "Base de datos local lista"
    }
} finally {
    if ($null -eq $envDatabaseUrlPrevio) { Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue }
    else { $env:DATABASE_URL = $envDatabaseUrlPrevio }
}

if ($contenido -match '^\s*DATABASE_URL=.+') {
    Write-Host "[INFO] DATABASE_URL definida: se aplicaran tambien las migraciones remotas." -ForegroundColor Gray
    & $venvPython manage.py migrate --database=remota --noinput 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Ok "Base remota actualizada" } else { Write-Warn "No se pudo migrar la base remota; el trabajo local continua normal." }
}

# ---------- [5/6] Datos de prueba ----------
if ($Seed) {
    Write-Step "[5/6] Cargando datos de prueba..."
    $env:DATABASE_URL = ""
    & $venvPython manage.py poblar_todo
    if ($LASTEXITCODE -ne 0) { Write-Warn "No se pudieron cargar los datos de prueba." }
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
}

# ---------- Cierre ----------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Setup COMPLETO" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Para iniciar el servidor:" -ForegroundColor Blue
Write-Host "  `"$venvPython`" manage.py runserver" -ForegroundColor White
Write-Host "  Abre http://127.0.0.1:8000/ en el navegador" -ForegroundColor Gray
Write-Host "Para ejecutar las pruebas:" -ForegroundColor Blue
Write-Host "  `"$venvPython`" manage.py test" -ForegroundColor White
Write-Host ""
