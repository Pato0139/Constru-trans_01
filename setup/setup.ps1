
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CONSTRU-TRANS - Setup automatico" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Verificar Python
Write-Host "[1/10] Verificando Python..." -ForegroundColor Yellow
$pythonCmd = $null
$pythonVersion = $null

# Buscar py.exe
try {
    $pyCmd = Get-Command py -ErrorAction Stop
    $pythonVersion = & py --version 2&gt;&1
    if ($pythonVersion -match "Python") {
        Write-Host "[OK] Python encontrado (py): $pythonVersion" -ForegroundColor Green
        $pythonCmd = "py"
    }
} catch {}

# Si no funciona, buscar python.exe
if (-not $pythonCmd) {
    try {
        $pythonVersion = & python --version 2&gt;&1
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
Write-Host "[2/10] Creando entorno virtual..." -ForegroundColor Yellow
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
Write-Host "[3/10] Instalando dependencias..." -ForegroundColor Yellow
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

# Paso 4: Instalar psycopg2-binary para PostgreSQL
Write-Host ""
Write-Host "[4/10] Instalando psycopg2-binary para PostgreSQL..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe -m pip install psycopg2-binary
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al instalar psycopg2-binary" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] psycopg2-binary instalado" -ForegroundColor Green

# Paso 5: Clonar repositorio Neon para obtener credenciales
Write-Host ""
Write-Host "[5/10] Obteniendo credenciales de Neon..." -ForegroundColor Yellow
$neonRepoPath = "Neon"
if (Test-Path $neonRepoPath) {
    Remove-Item -Recurse -Force $neonRepoPath
}
git clone https://github.com/Pato0139/Neon.git
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al clonar repositorio Neon" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] Repositorio Neon clonado" -ForegroundColor Green

# Paso 6: Configurar .env con credenciales de Neon
Write-Host ""
Write-Host "[6/10] Configurando archivo .env..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    # Copiar .env.example del repositorio Neon
    Copy-Item "$neonRepoPath\.env.example" ".env" -Force
    Write-Host "[OK] Archivo .env creado desde Neon" -ForegroundColor Green
    
    # Generar SECRET_KEY aleatorio
    $secretKey = & .\venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
    (Get-Content .env) -replace 'SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres', "SECRET_KEY=$secretKey" | Set-Content .env
    Write-Host "[OK] SECRET_KEY generado" -ForegroundColor Green
} else {
    Write-Host "[OK] Archivo .env ya existe" -ForegroundColor Green
}

# Paso 7: Eliminar repositorio Neon
Write-Host ""
Write-Host "[7/10] Eliminando repositorio Neon..." -ForegroundColor Yellow
if (Test-Path $neonRepoPath) {
    Remove-Item -Recurse -Force $neonRepoPath
    Write-Host "[OK] Repositorio Neon eliminado" -ForegroundColor Green
}

# Paso 8: Aplicar migraciones
Write-Host ""
Write-Host "[8/10] Aplicando migraciones..." -ForegroundColor Yellow
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

# Paso 9: Cargar datos de prueba (opcional)
Write-Host ""
Write-Host "[9/10] Cargando datos de prueba (opcional)..." -ForegroundColor Yellow
$seedScript = "scripts\seed_data.py"
if (Test-Path $seedScript) {
    & .\venv\Scripts\python.exe $seedScript
    Write-Host "[OK] Datos de prueba cargados" -ForegroundColor Green
} else {
    Write-Host "[OK] Script de datos no encontrado" -ForegroundColor Gray
}

# Paso 10: Final
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup COMPLETO!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el servidor:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "[INFO] Usando base de datos Neon PostgreSQL" -ForegroundColor Gray
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Read-Host "Presiona cualquier tecla para salir"
