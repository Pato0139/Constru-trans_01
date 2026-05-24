#!/bin/bash

# Colores para mejor legibilidad
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}================================================================"
echo -e "  CONSTRU-TRANS - Setup automatico (macOS/Linux)"
echo -e "================================================================"
echo -e "${NC}"

# Paso 1: Verificar Python
echo -e "${YELLOW}[1/7] Verificando Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo -e "${GREEN}[OK] Python encontrado: $($PYTHON_CMD --version)${NC}"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo -e "${GREEN}[OK] Python encontrado: $($PYTHON_CMD --version)${NC}"
else
    echo -e "${RED}[ERROR] Python no encontrado. Instala Python 3.11+${NC}"
    exit 1
fi

# Paso 2: Crear entorno virtual
echo -e ""
echo -e "${YELLOW}[2/7] Creando entorno virtual...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] Fallo al crear entorno virtual${NC}"
        exit 1
    fi
    echo -e "${GREEN}[OK] Entorno virtual creado${NC}"
else
    echo -e "${GREEN}[OK] Entorno virtual ya existe${NC}"
fi

# Paso 3: Instalar dependencias
echo -e ""
echo -e "${YELLOW}[3/8] Instalando dependencias...${NC}"
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al instalar dependencias${NC}"
    exit 1
fi
# Instalar psycopg2-binary para PostgreSQL (Neon)
pip install psycopg2-binary
echo -e "${GREEN}[OK] Dependencias instaladas${NC}"

# Paso 4: Clonar repositorio Neon para obtener credenciales
echo -e ""
echo -e "${YELLOW}[4/9] Obteniendo credenciales de Neon...${NC}"
neonRepoAvailable=false
if [ ! -d "neon-repo" ]; then
    if git clone https://github.com/Pato0139/Neon.git neon-repo; then
        neonRepoAvailable=true
        echo -e "${GREEN}[OK] Repositorio Neon clonado${NC}"
    else
        echo -e "${YELLOW}[ADVERTENCIA] No se pudo clonar el repositorio Neon. Continuando en modo local...${NC}"
    fi
else
    neonRepoAvailable=true
    echo -e "${GREEN}[OK] Repositorio Neon ya existe${NC}"
fi

# Paso 5: Verificar y configurar .env con credenciales de Neon
echo -e ""
echo -e "${YELLOW}[5/9] Verificando archivo .env...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}[OK] Archivo .env creado${NC}"
fi

if [ "$neonRepoAvailable" = true ] && [ -f "neon-repo/.env.example" ]; then
    # Obtener DATABASE_URL
    DB_URL=$(grep -E '^NEON_DATABASE_URL=' neon-repo/.env.example | sed 's/^NEON_DATABASE_URL=//')
    if [ -n "$DB_URL" ]; then
        sed -i.bak "s|^DATABASE_URL=.*|DATABASE_URL=$DB_URL|" .env && rm -f .env.bak
    fi

    # Obtener GMAIL_USER
    GMAIL_USER=$(grep -E '^GMAIL_USER=' neon-repo/.env.example | sed 's/^GMAIL_USER=//')
    if [ -n "$GMAIL_USER" ]; then
        sed -i.bak "s|^EMAIL_HOST_USER=.*|EMAIL_HOST_USER=$GMAIL_USER|" .env && rm -f .env.bak
        sed -i.bak "s|^DEFAULT_FROM_EMAIL=.*|DEFAULT_FROM_EMAIL=ConstruTrans <$GMAIL_USER>|" .env && rm -f .env.bak
    fi

    # Obtener GMAIL_APP_PASSWORD
    GMAIL_PASS=$(grep -E '^GMAIL_APP_PASSWORD=' neon-repo/.env.example | sed 's/^GMAIL_APP_PASSWORD=//')
    if [ -n "$GMAIL_PASS" ]; then
        sed -i.bak "s|^EMAIL_HOST_PASSWORD=.*|EMAIL_HOST_PASSWORD=$GMAIL_PASS|" .env && rm -f .env.bak
    fi

    echo -e "${GREEN}[OK] Credenciales de Neon y Gmail configuradas${NC}"
else
    echo -e "${YELLOW}[ADVERTENCIA] No se encontraron credenciales de Neon. El proyecto se ejecutará en modo local (SQLite) con modo invitado.${NC}"
fi

# Paso 6: Configurar archivos de settings para BD remota
echo -e ""
echo -e "${YELLOW}[6/9] Configurando settings para BD remota...${NC}"
python - <<END
import os
import re

BASE_DIR = os.getcwd()

# Configurar core/settings.py
settings_py = os.path.join(BASE_DIR, 'core', 'settings.py')
with open(settings_py, 'r', encoding='utf-8') as f:
    content = f.read()

# Asegurar que DATABASES['remota'] esté presente
if "DATABASES['remota'] = DATABASES['default'].copy()" not in content:
    # Buscar el bloque de if DATABASE_URL:
    pattern = re.compile(r'(if DATABASE_URL:\s+DATABASES = \{[^}]+})\s+else:', re.DOTALL)
    replacement = r'''\1
    # Agregar 'remota' usando la misma URL para sincronización
    DATABASES['remota'] = DATABASES['default'].copy()
else:'''
    content = pattern.sub(replacement, content)

# Asegurar que DATABASE_ROUTERS esté configurado
if "DATABASE_ROUTERS = ['core.routers.EnrutadorInventario']" not in content:
    # Reemplazar si está comentado o es []
    content = re.sub(r'(# Desactivar router temporalmente para simplificar\n)?DATABASE_ROUTERS = \[\]', r"DATABASE_ROUTERS = ['core.routers.EnrutadorInventario']", content)

with open(settings_py, 'w', encoding='utf-8') as f:
    f.write(content)

# Configurar core/settings/base.py
base_py = os.path.join(BASE_DIR, 'core', 'settings', 'base.py')
with open(base_py, 'r', encoding='utf-8') as f:
    base_content = f.read()

if "DATABASES['remota'] = DATABASES['default'].copy()" not in base_content:
    base_pattern = re.compile(r'(if DATABASE_URL:\s+DATABASES = \{[^}]+})\s+else:', re.DOTALL)
    base_replacement = r'''\1
    # Agregar 'remota' usando la misma URL para sincronización
    DATABASES['remota'] = DATABASES['default'].copy()
else:'''
    base_content = base_pattern.sub(base_replacement, base_content)

if "DATABASE_ROUTERS = ['core.routers.EnrutadorInventario']" not in base_content:
    base_content = re.sub(r'(# Desactivar router temporalmente para simplificar\n)?DATABASE_ROUTERS = \[\]', r"DATABASE_ROUTERS = ['core.routers.EnrutadorInventario']", base_content)

with open(base_py, 'w', encoding='utf-8') as f:
    f.write(base_content)

print('[OK] Settings configurados para BD remota')
END
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[ADVERTENCIA] No se pudo actualizar los settings automáticamente${NC}"
fi

# Paso 7: Aplicar migraciones
echo -e ""
echo -e "${YELLOW}[7/9] Aplicando migraciones...${NC}"
python manage.py migrate
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al aplicar migraciones${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Migraciones aplicadas${NC}"

# Paso 8: Cargar datos de la base de datos
echo -e ""
echo -e "${YELLOW}[8/9] Cargando datos de la base de datos...${NC}"
python manage.py seed_mer
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al cargar datos MER${NC}"
    exit 1
fi
python manage.py seed_data
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al cargar datos de prueba${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Datos cargados${NC}"

# Final
echo -e ""
echo -e "${GREEN}================================================================"
echo -e "  Setup COMPLETO!"
echo -e "================================================================"
echo -e "${NC}"
echo -e "${CYAN}Para iniciar el servidor:"
echo -e "  source venv/bin/activate"
echo -e "  python manage.py runserver"
echo -e "${NC}"
