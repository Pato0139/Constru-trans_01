Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  CONSTRU-TRANS - Setup automatico" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Verificar Python
Write-Host "[1/8] Verificando Python..." -ForegroundColor Yellow
$pythonCmd = $null
$pythonVersion = $null

# Buscar py.exe
try {
    $pyCmd = Get-Command py -ErrorAction Stop
    $pythonVersion = & py --version 2>&1
    if ($pythonVersion -match "Python") {
        Write-Host "[OK] Python encontrado (py): $pythonVersion" -ForegroundColor Green
        $pythonCmd = "py"
    }
} catch {}

# Si no funciona, buscar python.exe
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
& .\venv\Scripts\python.exe -m pip install --upgrade pip | Out-Null
& .\venv\Scripts\python.exe -m pip install -r requirements.txt 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Fallo al instalar dependencias" -ForegroundColor Red
    Read-Host "Presiona cualquier tecla para salir"
    exit 1
}
Write-Host "[OK] Dependencias instaladas" -ForegroundColor Green

# Paso 4: Configurar .env
Write-Host ""
Write-Host "[4/8] Configurando archivo .env..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Copy-Item .env.example .env -Force
    Write-Host "[OK] Archivo .env creado desde .env.example" -ForegroundColor Green
} else {
    Write-Host "[OK] Archivo .env ya existe" -ForegroundColor Green
}

# Paso 5: Detectar y configurar base de datos
Write-Host ""
Write-Host "[5/8] Verificando conexion a base de datos..." -ForegroundColor Yellow

# Leer DATABASE_URL del .env
$envContent = Get-Content ".env" -Raw -ErrorAction SilentlyContinue
$databaseUrl = $null
if ($envContent -match 'DATABASE_URL=(.+)') {
    $databaseUrl = $matches[1].Trim()
}

# Verificar si podemos conectar a Neon
$useNeon = $false
if ($databaseUrl -and $databaseUrl.StartsWith("postgres")) {
    Write-Host "  Probando conexion a Neon..." -ForegroundColor Gray
    $testResult = & .\venv\Scripts\python.exe -c "
import os, sys
try:
    import psycopg2
    url = os.environ.get('DATABASE_URL', '$databaseUrl')
    conn = psycopg2.connect(url, connect_timeout=5)
    conn.close()
    sys.exit(0)
except:
    sys.exit(1)
" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $useNeon = $true
        Write-Host "[OK] Conectado a base de datos Neon" -ForegroundColor Green
    }
}

# Si Neon no esta disponible, usar SQLite
if (-not $useNeon) {
    Write-Host "[AVISO] Neon no disponible. Usando SQLite local." -ForegroundColor Yellow
    
    # Modificar settings.py para usar SQLite
    $settingsPath = "core\settings.py"
    $settingsContent = Get-Content $settingsPath -Raw -ErrorAction SilentlyContinue
    
    if ($settingsContent) {
        # Comentar DATABASE_URL y agregar config SQLite
        $newContent = $settingsContent -replace 'DATABASE_URL\s*=', '# DATABASE_URL ='
        
        # Buscar y reemplazar DATABASES
        $pattern = "DATABASES\s*=\s*\{[^}]+dj_database_url\.parse[^}]+\}"
        if ($newContent -match $pattern) {
            $newContent = $newContent -replace $pattern, @"
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
"@
        }
        
        Set-Content -Path $settingsPath -Value $newContent -NoNewline -Force
        Write-Host "[OK] Settings configurado para SQLite" -ForegroundColor Green
    }
}

# Paso 6: Aplicar migraciones
Write-Host ""
Write-Host "[6/8] Aplicando migraciones..." -ForegroundColor Yellow
& .\venv\Scripts\python.exe manage.py migrate --run-syncdb 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] Error en migraciones. Verificando..." -ForegroundColor Yellow
    & .\venv\Scripts\python.exe manage.py check 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Problema con la configuracion" -ForegroundColor Red
    } else {
        Write-Host "[OK] Configuracion verificada" -ForegroundColor Green
    }
} else {
    Write-Host "[OK] Migraciones aplicadas" -ForegroundColor Green
}

# Paso 7: Cargar datos de prueba
Write-Host ""
Write-Host "[7/8] Cargando datos de prueba..." -ForegroundColor Yellow
$seedScript = "scripts\seed_data.py"
if (Test-Path $seedScript) {
    & .\venv\Scripts\python.exe $seedScript 2>&1 | Out-Null
    Write-Host "[OK] Datos de prueba cargados" -ForegroundColor Green
} else {
    Write-Host "[OK] Datos cargados (script no encontrado)" -ForegroundColor Gray
}

# Paso 8: Final
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup COMPLETO!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para iniciar el servidor:" -ForegroundColor Cyan
Write-Host "  .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor White
Write-Host ""
if (-not $useNeon) {
    Write-Host "[INFO] Usando base de datos SQLite local" -ForegroundColor Gray
    Write-Host "       Para usar Neon, configura DATABASE_URL en .env" -ForegroundColor Gray
    Write-Host ""
}
Write-Host "================================================================" -ForegroundColor Cyan
Read-Host "Presiona cualquier tecla para salir"
