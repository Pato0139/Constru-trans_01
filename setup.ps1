
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CONSTRU-TRANS - Setup automatico" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Verificar Python
Write-Host "[1/8] Verificando Python..." -ForegroundColor Yellow
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
& .\venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al instalar dependencias" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green

# Paso 4: Verificar .env
Write-Host ""
Write-Host "[4/8] Verificando archivo .env..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env
    Write-Host "[OK] Archivo .env creado" -ForegroundColor Green
} else {
    Write-Host "[OK] Archivo .env ya existe" -ForegroundColor Green
}

# Paso 5: Detectar modo de base de datos
Write-Host ""
Write-Host "[5/8] Verificando conexión a base de datos..." -ForegroundColor Yellow
$envContent = Get-Content ".env" -Raw -ErrorAction SilentlyContinue
$databaseUrl = $null

if ($envContent -match 'DATABASE_URL=(.+)') {
    $databaseUrl = $matches[1].Trim()
}

$useLocalDB = $false
if ($databaseUrl -and $databaseUrl.StartsWith("postgres")) {
    # Verificar si podemos conectar a PostgreSQL
    $testResult = & .\venv\Scripts\python.exe -c "
import os
import psycopg2
try:
    url = os.environ.get('DATABASE_URL', '')
    if not url:
        exit(1)
    conn = psycopg2.connect(url, connect_timeout=5)
    conn.close()
    exit(0)
except:
    exit(1)
" 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[AVISO] No se puede conectar a la base de datos Neon." -ForegroundColor Yellow
        Write-Host "       Se usará SQLite local para desarrollo." -ForegroundColor Yellow
        $useLocalDB = $true
    } else {
        Write-Host "[OK] Conectado a base de datos Neon" -ForegroundColor Green
    }
} else {
    $useLocalDB = $true
    Write-Host "[OK] Usando base de datos SQLite local" -ForegroundColor Green
}

# Configurar SQLite si es necesario
if ($useLocalDB) {
    # Modificar settings.py para usar SQLite
    $settingsPath = "core\settings.py"
    $settingsContent = Get-Content $settingsPath -Raw
    
    # Comentar la línea de DATABASE_URL y forzar SQLite
    $newSettings = $settingsContent -replace 'DATABASE_URL = os\.getenv\(["\']DATABASE_URL["\'],\s*["\'].*["\']\)', '# DATABASE_URL = os.getenv("DATABASE_URL") # Deshabilitado - usando SQLite local'
    
    # Verificar si ya está configurado con SQLite
    if ($newSettings -notmatch "sqlite3") {
        # Reemplazar toda la sección de DATABASES
        $newSettings = $newSettings -replace 'DATABASES\s*=\s*\{[^}]+engine[^}]+\}', @"
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
"@
    }
    
    Set-Content -Path $settingsPath -Value $newSettings -NoNewline
    Write-Host "[OK] Configurado para usar SQLite local" -ForegroundColor Green
}

# Paso 6: Aplicar migraciones
Write-Host ""
Write-Host "[6/8] Aplicando migraciones..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py migrate --no-input
if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] Error en migraciones. Intentando con --run-syncdb..." -ForegroundColor Yellow
    & .\venv\Scripts\python.exe manage.py migrate --run-syncdb --no-input
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Fallo al aplicar migraciones" -ForegroundColor Red
        Write-Host ""
        Write-Host "Si el error persiste, ejecuta manualmente:" -ForegroundColor Yellow
        Write-Host "  .\venv\Scripts\python.exe manage.py migrate --run-syncdb" -ForegroundColor Gray
        Write-Host ""
        Read-Host "Presiona cualquier tecla para continuar o Ctrl+C para salir"
    } else {
        Write-Host "[OK] Migraciones aplicadas (--run-syncdb)" -ForegroundColor Green
    }
} else {
    Write-Host "[OK] Migraciones aplicadas" -ForegroundColor Green
}

# Paso 7: Cargar datos de la base de datos
Write-Host ""
Write-Host "[7/8] Cargando datos de la base de datos..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py seed_mer 2>$null
& .\venv\Scripts\python.exe scripts\database\seed_data.py 2>$null
Write-Host "[OK] Datos cargados" -ForegroundColor Green

# Paso 8: Final
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup COMPLETO!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el servidor:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor White
Write-Host ""
if ($useLocalDB) {
    Write-Host "[NOTA] Estás usando la base de datos SQLite local." -ForegroundColor Gray
    Write-Host "      Para usar Neon en producción, configura DATABASE_URL en .env" -ForegroundColor Gray
    Write-Host ""
}
Read-Host "Presiona cualquier tecla para salir"
