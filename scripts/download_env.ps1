# Script para descargar .env desde un repositorio privado y fusionar con el local
param(
    [string]$RepoUrl = "https://github.com/Pato0139/Neon.git",
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

# Rutas
$TempDir = ".temp_env_repo"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TargetEnvPath = Join-Path $ProjectRoot ".env"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Configurando .env para el proyecto..." -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Eliminar directorio temporal si existe
if (Test-Path $TempDir) {
    Remove-Item -Path $TempDir -Recurse -Force
}

function Read-EnvFile($Path) {
    $env = @{}
    if (Test-Path $Path) {
        foreach ($line in Get-Content $Path) {
            $line = $line.Trim()
            if (-not $line -or $line.StartsWith("#")) {
                continue
            }
            $equalsIndex = $line.IndexOf("=")
            if ($equalsIndex -gt 0) {
                $key = $line.Substring(0, $equalsIndex).Trim()
                $value = $line.Substring($equalsIndex + 1).Trim()
                if ($value.StartsWith('"') -and $value.EndsWith('"')) {
                    $value = $value.Substring(1, $value.Length - 2)
                }
                $env[$key] = $value
            }
        }
    }
    return $env
}

function Write-EnvFile($Path, $EnvData) {
    $lines = @()
    foreach ($key in $EnvData.Keys) {
        $value = $EnvData[$key]
        if ($value -match '\s' -or $value -match '"') {
            $value = "`"$($value -replace '"', '\"')`""
        }
        $lines += "$key=$value"
    }
    $lines | Out-File -FilePath $Path -Encoding utf8
}

try {
    # Leer archivo .env local si existe
    $localEnv = Read-EnvFile -Path $TargetEnvPath
    $hasLocalEnv = $localEnv.Count -gt 0

    # Clonar el repositorio
    Write-Host "[1/4] Clonando repositorio Neon..." -ForegroundColor Yellow
    git clone --depth 1 --branch $Branch $RepoUrl $TempDir
    if ($LASTEXITCODE -ne 0) {
        throw "Error al clonar el repositorio. Verifica la URL y tus permisos."
    }

    # Verificar si existe .env o .env.example en el repositorio
    $SourceEnvPath = Join-Path $TempDir ".env"
    $SourceEnvExamplePath = Join-Path $TempDir ".env.example"
    
    if (-not (Test-Path $SourceEnvPath) -and -not (Test-Path $SourceEnvExamplePath)) {
        throw "No se encontro el archivo .env ni .env.example en el repositorio."
    }

    # Leer el archivo fuente
    $sourcePath = if (Test-Path $SourceEnvPath) { $SourceEnvPath } else { $SourceEnvExamplePath }
    $sourceEnv = Read-EnvFile -Path $sourcePath

    # Fusionar: priorizar variables locales, agregar nuevas del fuente
    $finalEnv = @{}
    foreach ($key in $sourceEnv.Keys) {
        if ($localEnv.ContainsKey($key)) {
            $finalEnv[$key] = $localEnv[$key]
        } else {
            $finalEnv[$key] = $sourceEnv[$key]
        }
    }
    # Agregar variables locales que no están en el fuente
    foreach ($key in $localEnv.Keys) {
        if (-not $finalEnv.ContainsKey($key)) {
            $finalEnv[$key] = $localEnv[$key]
        }
    }

    # Escribir el archivo final
    Write-Host "[2/4] Fusionando variables de entorno..." -ForegroundColor Yellow
    Write-EnvFile -Path $TargetEnvPath -EnvData $finalEnv
    
    if ($hasLocalEnv) {
        Write-Host "  Fusionado con el .env local existente" -ForegroundColor Green
    } else {
        Write-Host "  Creado nuevo .env desde el repositorio" -ForegroundColor Yellow
    }

    Write-Host "[3/4] Limpiando archivos temporales..." -ForegroundColor Yellow
    Remove-Item -Path $TempDir -Recurse -Force

    Write-Host "[4/4] Completado!" -ForegroundColor Green
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  .env configurado exitosamente!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "  ERROR: $_" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host 'Si el repositorio es privado, asegurate de:' -ForegroundColor Yellow
    Write-Host '  1. Tener acceso al repositorio' -ForegroundColor Yellow
    Write-Host '  2. Estar autenticado en Git (git config --global user.name / user.email)' -ForegroundColor Yellow
    Write-Host '  3. Usar una URL con token si es necesario (ej: https://TOKEN@github.com/usuario/repo.git)' -ForegroundColor Yellow
    Write-Host ""
    
    # Si falla, copiar desde .env.example local (funciona sin BD remota!)
    $LocalEnvExample = Join-Path $ProjectRoot ".env.example"
    if (Test-Path $LocalEnvExample) {
        Write-Host ""
        Write-Host "================================================================" -ForegroundColor Cyan
        Write-Host "  Copiando .env.example local como .env..." -ForegroundColor Cyan
        Write-Host "  (funciona perfectamente sin BD remota!)" -ForegroundColor Gray
        Write-Host "================================================================" -ForegroundColor Cyan
        
        Copy-Item -Path $LocalEnvExample -Destination $TargetEnvPath -Force
        Write-Host "  ✔️ Copiado exitosamente!" -ForegroundColor Green
        
        Write-Host ""
        Write-Host "Siguientes pasos:" -ForegroundColor Yellow
        Write-Host "  1. Genera una SECRET_KEY (ejecuta esto):" -ForegroundColor White
        Write-Host '     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"' -ForegroundColor Gray
        Write-Host ""
        Write-Host "  2. Edita el archivo .env y pega la clave generada" -ForegroundColor White
        Write-Host ""
        Write-Host "  3. (Opcional) Si quieres usar la BD remota Neon, configura DATABASE_URL" -ForegroundColor White
        Write-Host ""
        Write-Host "¡Listo! Ahora puedes ejecutar: python manage.py runserver" -ForegroundColor Green
    } else {
        Write-Host "ERROR: No se encontro .env.example en el proyecto!" -ForegroundColor Red
    }

    # Limpiar si hubo error
    if (Test-Path $TempDir) {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    exit 0
}
