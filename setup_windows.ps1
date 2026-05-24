
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CONSTRU-TRANS - Setup automatico" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Verificar Python
Write-Host "[1/7] Verificando Python..." -ForegroundColor Yellow
$pythonFound = $false
$pythonCmd = $null

# Buscar py.exe primero
try {
    $pyCmd = Get-Command py -ErrorAction Stop
    $versionOutput = & py --version 2>&1
    if ($versionOutput -match "Python (\d+\.\d+\.\d+)") {
        Write-Host "[OK] Python encontrado (py): $versionOutput" -ForegroundColor Green
        $pythonFound = $true
        $pythonCmd = "py"
    }
} catch {
    # py.exe no encontrado
}

# Si no encontramos py, buscar python.exe
if (-not $pythonFound) {
    try {
        $pythonCmdPath = Get-Command python -ErrorAction Stop
        $versionOutput = & python --version 2>&1
        if ($versionOutput -match "Python (\d+\.\d+\.\d+)") {
            Write-Host "[OK] Python encontrado: $versionOutput" -ForegroundColor Green
            $pythonFound = $true
            $pythonCmd = "python"
        } else {
            Write-Host "[ADVERTENCIA] El comando 'python' parece ser el alias de Windows Store." -ForegroundColor Yellow
            Write-Host "  Por favor, desactiva los alias de Python en: Settings > Apps > Advanced app settings > App execution aliases" -ForegroundColor Yellow
            Write-Host "  O instala Python desde python.org y asegúrate de marcar 'Add Python to PATH' durante la instalación." -ForegroundColor Yellow
        }
    } catch {
        # python.exe no encontrado
    }
}

# Si aún no encontramos Python, guiar al usuario
if (-not $pythonFound) {
    Write-Host ""
    Write-Host "[ERROR] Python no encontrado." -ForegroundColor Red
    Write-Host ""
    Write-Host "Por favor, sigue estos pasos:" -ForegroundColor Yellow
    Write-Host "1. Descarga Python 3.11 o superior desde: https://www.python.org/downloads/" -ForegroundColor White
    Write-Host "2. Durante la instalación, MARCA la opción 'Add Python to PATH'" -ForegroundColor Cyan
    Write-Host "3. Cierra y abre PowerShell nuevamente" -ForegroundColor White
    Write-Host "4. Vuelve a ejecutar este script" -ForegroundColor White
    Write-Host ""
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}

# Paso 2: Crear entorno virtual
Write-Host ""
Write-Host "[2/7] Creando entorno virtual..." -ForegroundColor Yellow
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
& .\venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al instalar dependencias" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
# Instalar psycopg2-binary para PostgreSQL (Neon)
& .\venv\Scripts\python.exe -m pip install psycopg2-binary
Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green

# Paso 4: Descargar y fusionar credenciales de Neon usando el script dedicado
Write-Host ""
Write-Host "[4/9] Obteniendo credenciales de Neon..." -ForegroundColor Yellow
& .\scripts\download_env.ps1

# Eliminar neon-repo si existe (para limpieza)
if (Test-Path "neon-repo") {
    Write-Host "[LIMPIEZA] Eliminando carpeta neon-repo..." -ForegroundColor Cyan
    Remove-Item -Path "neon-repo" -Recurse -Force
}

# Paso 5: Verificar archivo .env
Write-Host ""
Write-Host "[5/9] Verificando archivo .env..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "[OK] Archivo .env creado" -ForegroundColor Green
} else {
    Write-Host "[OK] Archivo .env existe" -ForegroundColor Green
}

# Paso 6: Configurar archivos de settings para BD remota
Write-Host ""
Write-Host "[6/9] Configurando settings para BD remota..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe .\scripts\configure_settings.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ADVERTENCIA] No se pudo actualizar los settings automaticamente" -ForegroundColor Yellow
}

# Paso 7: Aplicar migraciones
Write-Host ""
Write-Host "[7/9] Aplicando migraciones..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al aplicar migraciones" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] Migraciones aplicadas" -ForegroundColor Green

# Paso 8: Cargar datos de la base de datos
Write-Host ""
Write-Host "[8/9] Cargando datos de la base de datos..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py seed_mer
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al cargar datos MER" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
& .\venv\Scripts\python.exe manage.py seed_data
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al cargar datos de prueba" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] Datos cargados" -ForegroundColor Green

# Final
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup COMPLETO!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el servidor:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor White
Write-Host ""
Read-Host "Presiona cualquier tecla para salir"
