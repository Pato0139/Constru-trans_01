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
Write-Host "  Configurando .env para el proyecto..." -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Eliminar directorio temporal si existe
if (Test-Path $TempDir) {
    Remove-Item -Path $TempDir -Recurse -Force
}

try {
    # Clonar el repositorio
    Write-Host "[1/3] Clonando repositorio Neon..." -ForegroundColor Yellow
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

    # Copiar archivo al proyecto
    Write-Host "[2/3] Copiando archivo de configuracion..." -ForegroundColor Yellow
    if (Test-Path $SourceEnvPath) {
        Copy-Item -Path $SourceEnvPath -Destination $TargetEnvPath -Force
        Write-Host "  Copiado .env desde el repositorio" -ForegroundColor Green
    } else {
        Copy-Item -Path $SourceEnvExamplePath -Destination $TargetEnvPath -Force
        Write-Host "  Copiado .env.example como .env" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "IMPORTANTE: Debes editar el archivo .env y configurar:" -ForegroundColor Red
        Write-Host "  - SECRET_KEY (genera una clave aleatoria)" -ForegroundColor Red
        Write-Host "  - DATABASE_URL (URL de tu base de datos Neon)" -ForegroundColor Red
        Write-Host "  - Otras credenciales necesarias" -ForegroundColor Red
    }

    Write-Host "[3/3] Limpiando archivos temporales..." -ForegroundColor Yellow
    Remove-Item -Path $TempDir -Recurse -Force

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
    
    # Si falla, intentar copiar desde .env.example local
    $LocalEnvExample = Join-Path $ProjectRoot ".env.example"
    if (Test-Path $LocalEnvExample) {
        Write-Host "Intentando copiar desde .env.example local..." -ForegroundColor Yellow
        Copy-Item -Path $LocalEnvExample -Destination $TargetEnvPath -Force
        Write-Host "  Copiado .env.example local como .env" -ForegroundColor Green
    }

    # Limpiar si hubo error
    if (Test-Path $TempDir) {
        Remove-Item -Path $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    exit 1
}
