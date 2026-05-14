# Script para descargar .env desde un repositorio privado
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
Write-Host "  Descargando .env desde repositorio privado..." -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Eliminar directorio temporal si existe
if (Test-Path $TempDir) {
    Remove-Item -Path $TempDir -Recurse -Force
}

try {
    # Clonar el repositorio
    Write-Host "[1/3] Clonando repositorio..." -ForegroundColor Yellow
    git clone --depth 1 --branch $Branch $RepoUrl $TempDir 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Error al clonar el repositorio. Verifica la URL y tus permisos."
    }

    # Verificar que exista .env en el repositorio
    $SourceEnvPath = Join-Path $TempDir ".env"
    if (-not (Test-Path $SourceEnvPath)) {
        throw "No se encontró el archivo .env en el repositorio."
    }

    # Copiar .env al proyecto
    Write-Host "[2/3] Copiando .env al proyecto..." -ForegroundColor Yellow
    Copy-Item -Path $SourceEnvPath -Destination $TargetEnvPath -Force

    Write-Host "[3/3] Limpiando archivos temporales..." -ForegroundColor Yellow
    Remove-Item -Path $TempDir -Recurse -Force

    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  ✓ .env descargado exitosamente!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "  ERROR: $_" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host 'Si el repositorio es privado, asegúrate de:' -ForegroundColor Yellow
    Write-Host '  1. Tener acceso al repositorio' -ForegroundColor Yellow
    Write-Host '  2. Estar autenticado en Git (git config --global user.name / user.email)' -ForegroundColor Yellow
    Write-Host '  3. Usar una URL con token si es necesario (ej: https://TOKEN@github.com/usuario/repo.git)' -ForegroundColor Yellow
    Write-Host ""

    # Limpiar si hubo error
    if (Test-Path $TempDir) {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    exit 1
}
