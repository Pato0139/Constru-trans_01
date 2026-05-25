#!/usr/bin/env bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo -e "${CYAN}================================================================"
echo -e "  CONSTRU-TRANS - Setup automático (macOS/Linux)"
echo -e "================================================================"
echo -e "${NC}"

echo -e "${YELLOW}[1/8] Verificando Python...${NC}"
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python 3 no encontrado. Instala Python 3.11+ y vuelve a intentar.${NC}"
    exit 1
fi

if ! $PYTHON_CMD -c 'import sys; sys.exit(not (sys.version_info >= (3, 11)))' >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] Python 3.11 o superior es requerido. Encontrado: $($PYTHON_CMD --version)${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] Python encontrado: $($PYTHON_CMD --version)${NC}"

echo -e ""
echo -e "${YELLOW}[2/8] Creando entorno virtual...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}[OK] Entorno virtual creado${NC}"
else
    echo -e "${GREEN}[OK] Entorno virtual ya existe${NC}"
fi

source venv/bin/activate

echo -e ""
echo -e "${YELLOW}[3/8] Instalando dependencias...${NC}"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo -e "${GREEN}[OK] Dependencias instaladas${NC}"

echo -e ""
echo -e "${YELLOW}[4/8] Configurando archivo .env local...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp ".env.example" .env
        echo -e "${GREEN}[OK] Archivo .env creado desde .env.example${NC}"
    else
        cat > .env <<'EOF'
DJANGO_ENV=development
SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=http://127.0.0.1:8000,http://localhost:8000
DATABASE_URL=
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
DEFAULT_FROM_EMAIL=Constru-Trans <no-reply@example.com>
SERVER_EMAIL=Constru-Trans <no-reply@example.com>
USE_S3=False
EOF
        echo -e "${GREEN}[OK] Archivo .env creado con valores mínimos por defecto${NC}"
    fi

    SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres|SECRET_KEY=$SECRET_KEY|" .env
    else
        sed -i "s|SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres|SECRET_KEY=$SECRET_KEY|" .env
    fi
    echo -e "${GREEN}[OK] SECRET_KEY generado${NC}"
else
    echo -e "${GREEN}[OK] Archivo .env ya existe${NC}"
fi

echo -e ""
echo -e "${YELLOW}[7/8] Aplicando migraciones...${NC}"
python manage.py migrate --run-syncdb || {
    echo -e "${YELLOW}[AVISO] Migraciones fallaron. Verificando configuración...${NC}"
    python manage.py check
    echo -e "${GREEN}[OK] Configuración verificada${NC}"
}

echo -e "${GREEN}[OK] Migraciones completadas${NC}"

db_url=""
if [ -f ".env" ]; then
    db_url=$(grep -E '^DATABASE_URL=' .env | cut -d'=' -f2-)
fi

echo -e ""
echo -e "${GREEN}================================================================"
echo -e "  Setup COMPLETO!"
echo -e "================================================================"
echo -e "${NC}"
echo -e "${CYAN}Para iniciar el servidor:"
echo -e "  source venv/bin/activate"
echo -e "  python manage.py runserver"
echo -e "${NC}"
if [ -n "$db_url" ]; then
    echo -e "${YELLOW}[INFO] Usando base de datos Neon PostgreSQL${NC}"
else
    echo -e "${YELLOW}[INFO] Usando base de datos SQLite local${NC}"
fi
echo -e ""
echo -e "================================================================"
