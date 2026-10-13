$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "CONSTRU-TRANS - Instalador para Windows" -ForegroundColor Cyan
Write-Host ""

function Test-PythonEnvironment {
    param([string]$PythonPath)

    if (-not (Test-Path $PythonPath -PathType Leaf)) {
        return $null
    }

    $probe = "import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 11) and sys.prefix != sys.base_prefix else 1)"
    try {
        $result = & $PythonPath -c $probe 2>&1
        if ($LASTEXITCODE -eq 0) {
            return ($result | Select-Object -Last 1).ToString().Trim()
        }
    } catch {
        return $null
    }

    return $null
}

$venvPath = $null
$venvPython = $null
$pythonVersion = $null
$projectPrefix = $projectRoot.TrimEnd("\") + "\"

if ($env:VIRTUAL_ENV) {
    $activeEnvironment = [System.IO.Path]::GetFullPath($env:VIRTUAL_ENV).TrimEnd("\")
    if ($activeEnvironment.StartsWith($projectPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        $activePython = Join-Path $activeEnvironment "Scripts\python.exe"
        $activeVersion = Test-PythonEnvironment $activePython
        if ($activeVersion) {
            $venvPath = $activeEnvironment
            $venvPython = $activePython
            $pythonVersion = $activeVersion
            Write-Host "[OK] Se usará el entorno virtual activo: $venvPath" -ForegroundColor Green
        }
    }
}

if (-not $venvPython) {
    $environmentCandidates = @(
        (Join-Path $projectRoot ".venv"),
        (Join-Path $projectRoot "venv"),
        (Join-Path $projectRoot ".venv-1")
    )
    $environmentCandidates += Get-ChildItem -Path $projectRoot -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like ".venv-*" -and $_.Name -ne ".venv-1" } |
        Sort-Object Name |
        ForEach-Object { $_.FullName }

    foreach ($candidatePath in $environmentCandidates) {
        $candidatePython = Join-Path $candidatePath "Scripts\python.exe"
        $candidateVersion = Test-PythonEnvironment $candidatePython
        if ($candidateVersion) {
            $venvPath = $candidatePath
            $venvPython = $candidatePython
            $pythonVersion = $candidateVersion
            Write-Host "[OK] Se reutilizará el entorno virtual existente: $venvPath" -ForegroundColor Green
            break
        }
    }
}

if (-not $venvPython) {
    $pythonCandidates = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $pythonCandidates += @(
            @{ Command = "py"; Args = @("-3.14") },
            @{ Command = "py"; Args = @("-3.13") },
            @{ Command = "py"; Args = @("-3.12") },
            @{ Command = "py"; Args = @("-3.11") }
        )
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCandidates += @{ Command = "python"; Args = @() }
    }

    $pythonCommand = $null
    $pythonArgs = @()
    $versionCheck = "import sys; print(sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"

    foreach ($candidate in $pythonCandidates) {
        try {
            $commandArgs = @($candidate.Args) + @("-c", $versionCheck)
            $versionOutput = & $candidate.Command @commandArgs 2>&1
            if ($LASTEXITCODE -eq 0) {
                $pythonCommand = $candidate.Command
                $pythonArgs = $candidate.Args
                $pythonVersion = ($versionOutput | Select-Object -Last 1).ToString().Trim()
                break
            }
        } catch {
            continue
        }
    }

    if (-not $pythonCommand) {
        Write-Host "[ERROR] No encontré un Python 3.11 o superior ni un entorno virtual utilizable." -ForegroundColor Red
        Write-Host "Instala Python desde https://www.python.org/downloads/ o activa el entorno del proyecto y vuelve a intentarlo." -ForegroundColor Yellow
        exit 1
    }

    $venvPath = Join-Path $projectRoot ".venv"
    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    if (Test-Path $venvPath) {
        Write-Host "[ERROR] La carpeta .venv existe pero no contiene un entorno válido. No se borró ni modificó." -ForegroundColor Red
        Write-Host "Activa otro entorno válido o revisa .venv antes de volver a ejecutar el setup." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "[OK] Python $pythonVersion; creando el entorno .venv..." -ForegroundColor Green
    & $pythonCommand @pythonArgs -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] No se pudo crear el entorno virtual .venv." -ForegroundColor Red
        exit 1
    }
    $pythonVersion = Test-PythonEnvironment $venvPython
    if (-not $pythonVersion) {
        Write-Host "[ERROR] El entorno .venv recién creado no es válido. No se eliminaron archivos." -ForegroundColor Red
        exit 1
    }
}

Write-Host "[OK] Entorno listo con Python $pythonVersion" -ForegroundColor Green

Write-Host "[OK] Instalando dependencias de requirements.txt..."
& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] No se pudo actualizar pip." -ForegroundColor Red
    exit 1
}
& $venvPython -m pip install --prefer-binary -r (Join-Path $projectRoot "requirements.txt")
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Falló la instalación de dependencias. Revisa la conexión a Internet y requirements.txt." -ForegroundColor Red
    exit 1
}

$envPath = Join-Path $projectRoot ".env"
if (-not (Test-Path $envPath)) {
    $secretKey = & $venvPython -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    if ($LASTEXITCODE -ne 0 -or -not $secretKey) {
        Write-Host "[ERROR] No se pudo generar SECRET_KEY para .env." -ForegroundColor Red
        exit 1
    }
    $envContent = @(
        "DJANGO_ENV=development",
        "SECRET_KEY=$($secretKey.Trim())",
        "DEBUG=True",
        "ALLOWED_HOSTS=localhost,127.0.0.1",
        "CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000",
        "DATABASE_URL=",
        "OPENWEATHER_API_KEY="
    ) -join [Environment]::NewLine
    [System.IO.File]::WriteAllText($envPath, $envContent, [System.Text.UTF8Encoding]::new($false))
    Write-Host "[OK] Se creó .env para desarrollo local."
} else {
    Write-Host "[OK] Se conserva el .env existente."
}

$previousDatabaseUrl = $env:DATABASE_URL
try {
    $env:DATABASE_URL = ""
    Write-Host "[OK] Verificando configuración Django..."
    & $venvPython manage.py check
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] La verificación de Django falló." -ForegroundColor Red
        exit 1
    }

    Write-Host "[OK] Aplicando migraciones a la base SQLite local..."
    & $venvPython manage.py migrate --run-syncdb
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallaron las migraciones de la base local." -ForegroundColor Red
        exit 1
    }
} finally {
    if ($null -eq $previousDatabaseUrl) {
        Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    } else {
        $env:DATABASE_URL = $previousDatabaseUrl
    }
}

Write-Host ""
Write-Host "Setup completado." -ForegroundColor Green
Write-Host "Para iniciar el servidor:"
Write-Host "  `"$venvPython`" manage.py runserver"
