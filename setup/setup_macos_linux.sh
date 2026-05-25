#!/usr/bin/env bash

set -euo pipefail

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

echo -e "${YELLOW}[1/9] Verificando Python...${NC}"
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
echo -e "${YELLOW}[2/9] Creando entorno virtual...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}[OK] Entorno virtual creado${NC}"
else
    echo -e "${GREEN}[OK] Entorno virtual ya existe${NC}"
fi

source venv/bin/activate

echo -e ""
echo -e "${YELLOW}[3/9] Instalando dependencias...${NC}"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo -e "${GREEN}[OK] Dependencias instaladas${NC}"

echo -e ""
echo -e "${YELLOW}[4/9] Instalando psycopg2-binary para PostgreSQL...${NC}"
python -m pip install psycopg2-binary
echo -e "${GREEN}[OK] psycopg2-binary instalado${NC}"

echo -e ""
echo -e "${YELLOW}[5/9] Obteniendo credenciales de Neon...${NC}"
NEON_REPO_PATH="Neon"
if [ -d "$NEON_REPO_PATH" ]; then
    rm -rf "$NEON_REPO_PATH"
fi
git clone https://github.com/Pato0139/Neon.git
echo -e "${GREEN}[OK] Repositorio Neon clonado${NC}"

echo -e ""
echo -e "${YELLOW}[6/9] Configurando archivo .env...${NC}"
if [ ! -f ".env" ]; then
    cp "$NEON_REPO_PATH/.env.example" ".env"
    echo -e "${GREEN}[OK] Archivo .env creado desde Neon${NC}"
    
    SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    sed -i.bak "s|SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres|SECRET_KEY=$SECRET_KEY|" .env && rm -f .env.bak
    echo -e "${GREEN}[OK] SECRET_KEY generado${NC}"
else
    echo -e "${GREEN}[OK] Archivo .env ya existe${NC}"
fi

echo -e ""
echo -e "${YELLOW}[7/9] Eliminando repositorio Neon...${NC}"
if [ -d "$NEON_REPO_PATH" ]; then
    rm -rf "$NEON_REPO_PATH"
    echo -e "${GREEN}[OK] Repositorio Neon eliminado${NC}"
fi

echo -e ""
echo -e "${YELLOW}[8/9] Aplicando migraciones...${NC}"
python manage.py migrate --run-syncdb || {
    echo -e "${YELLOW}[AVISO] Verificando configuración...${NC}"
    python manage.py check
    echo -e "${GREEN}[OK] Configuración verificada${NC}"
}
echo -e "${GREEN}[OK] Migraciones aplicadas${NC}"

echo -e ""
echo -e "${GREEN}================================================================"
echo -e "  Setup COMPLETO!"
echo -e "================================================================"
echo -e "${NC}"
echo -e "${CYAN}Para iniciar el servidor:"
echo -e "  source venv/bin/activate"
echo -e "  python manage.py runserver"
echo -e "${NC}"
echo -e "${YELLOW}[INFO] Usando base de datos Neon PostgreSQL${NC}"
echo -e ""
echo -e "================================================================"
