
#!/usr/bin/env bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;37m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo -e "${CYAN}================================================================"
echo -e "${BLUE}CONSTRU-TRANS - Setup automático (macOS/Linux)"
echo -e "${CYAN}================================================================" 
echo -e "${NC}"

echo -e "${BLUE}[1/5] Verificando Python..."
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python 3 no encontrado. Instala Python 3.11+ y vuelve a intentar."
    exit 1
fi

if ! $PYTHON_CMD -c 'import sys; sys.exit(not (sys.version_info >= (3, 11)))' >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] Python 3.11 o superior es requerido. Encontrado: $($PYTHON_CMD --version)"
    exit 1
fi

echo -e "${GREEN}[OK] Python encontrado: $($PYTHON_CMD --version)"

echo -e ""
echo -e "${BLUE}[2/5] Creando entorno virtual..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}[OK] Entorno virtual creado"
else
    echo -e "${GREEN}[OK] Entorno virtual ya existe"
fi

source venv/bin/activate

echo -e ""
echo -e "${BLUE}[3/5] Instalando dependencias..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo -e "${GREEN}[OK] Dependencias instaladas"

echo -e ""
echo -e "${BLUE}[4/5] Configurando archivo .env local..."
echo -e ""
echo -e "${CYAN}================================================================"
echo -e "${BLUE}OBTENIENDO CREDENCIALES AUTOMATICAMENTE"
echo -e "${CYAN}================================================================"
echo -e "${NC}"

NEON_REPO_URL="https://github.com/Pato0139/Neon.git"
TEMP_DIR="temp_neon_repo"
ENV_CREADO=false

# Limpiar temporal si existe
trap 'if [ -d "$TEMP_DIR" ]; then rm -rf "$TEMP_DIR"; fi' EXIT

if command -v git >/dev/null 2>&1; then
    echo -e "${BLUE}[1/3] Clonando repositorio de credenciales..."
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    if git clone --depth 1 "$NEON_REPO_URL" "$TEMP_DIR" 2>/dev/null; then
        echo -e "${GREEN}[OK] Repositorio clonado"
        
        echo -e "${BLUE}[2/3] Copiando archivo de configuración..."
        if [ -f "$TEMP_DIR/.env.example" ]; then
            cp "$TEMP_DIR/.env.example" ".env"
            echo -e "${GREEN}[OK] Archivo .env creado con todas las credenciales!"
            ENV_CREADO=true
        else
            echo -e "${YELLOW}[AVISO] No se encontró .env.example en el repo"
        fi
        
        echo -e "${BLUE}[3/3] Limpiando repositorio temporal..."
        rm -rf "$TEMP_DIR"
        echo -e "${GREEN}[OK] Repositorio temporal eliminado"
    else
        echo -e "${YELLOW}[AVISO] No se pudo clonar el repositorio"
    fi
else
    echo -e "${YELLOW}[AVISO] Git no está instalado"
fi

# Si no se pudo crear desde el repo, creamos uno básico
if [ "$ENV_CREADO" = false ]; then
    echo -e ""
    echo -e "${BLUE}[OK] Generando configuración básica..."
    DJANGO_ENV="development"
    SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
    
    cat > ".env" <<EOF
# Variables minimas para desarrollo local
DJANGO_ENV=$DJANGO_ENV
SECRET_KEY=$SECRET_KEY
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# Base de datos local por defecto (SQLite)
DATABASE_URL=

# Email en desarrollo
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=Constru-Trans <no-reply@example.com>
SERVER_EMAIL=Constru-Trans <no-reply@example.com>

# Almacenamiento opcional en S3
USE_S3=False
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=
AWS_S3_ENDPOINT_URL=
AWS_S3_REGION_NAME=us-east-1
EOF

    echo -e "${GREEN}[OK] Archivo .env creado con valores básicos"
fi

# Verificamos si tenemos DATABASE_URL
DATABASE_URL=""
if [ -f ".env" ]; then
    DATABASE_URL=$(grep -E '^DATABASE_URL=' .env | cut -d'=' -f2-)
fi

echo -e ""
if [ -n "$DATABASE_URL" ]; then
    echo -e "${GREEN}[OK] DATABASE_URL configurada! Modo híbrido activado (SQLite local + Neon remota)"
else
    echo -e "${GRAY}[INFO] Usando solo base de datos SQLite local (modo offline)"
fi

echo -e ""
echo -e "${BLUE}[5/5] Aplicando migraciones..."
python manage.py migrate --run-syncdb || {
    echo -e "${YELLOW}[AVISO] Migraciones fallaron. Verificando configuración..."
    python manage.py check
    echo -e "${GREEN}[OK] Configuración verificada"
}

echo -e "${GREEN}[OK] Migraciones completadas"

echo -e ""
echo -e "${CYAN}================================================================"
echo -e "${BLUE}Setup COMPLETO!"
echo -e "${CYAN}================================================================"
echo -e "${NC}"
echo -e "${BLUE}Para iniciar el servidor:"
echo -e "${WHITE}source venv/bin/activate"
echo -e "${WHITE}python manage.py runserver"
echo -e "${NC}"
echo -e ""
echo -e "${CYAN}================================================================"

