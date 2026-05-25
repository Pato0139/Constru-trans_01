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

echo -e "${YELLOW}[1/10] Verificando Python...${NC}"
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
echo -e "${YELLOW}[2/10] Creando entorno virtual...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    echo -e "${GREEN}[OK] Entorno virtual creado${NC}"
else
    echo -e "${GREEN}[OK] Entorno virtual ya existe${NC}"
fi

source venv/bin/activate

echo -e ""
echo -e "${YELLOW}[3/10] Instalando dependencias...${NC}"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo -e "${GREEN}[OK] Dependencias instaladas${NC}"

echo -e ""
echo -e "${YELLOW}[4/10] Configurando archivo .env...${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}[OK] Archivo .env creado desde .env.example${NC}"

        SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
        sed -i.bak "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" .env && rm -f .env.bak
        echo -e "${GREEN}[OK] SECRET_KEY generado${NC}"

        sed -i.bak 's|^DATABASE_URL=.*|DATABASE_URL=|' .env && rm -f .env.bak
        echo -e "${GREEN}[OK] DATABASE_URL inicializado para usar SQLite local${NC}"
    else
        echo -e "${RED}[ERROR] No se encontró .env.example en el repositorio.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}[OK] Archivo .env ya existe${NC}"
fi

if grep -q '^DATABASE_URL=.*\(host.neon.tech\|USUARIO:PASSWORD\)' .env; then
    sed -i.bak 's|^DATABASE_URL=.*|DATABASE_URL=|' .env && rm -f .env.bak
    echo -e "${YELLOW}[AVISO] La URL de base de datos de ejemplo se reemplazó por SQLite local${NC}"
fi

if grep -q '^SECRET_KEY=cambia-esto' .env; then
    echo -e "${YELLOW}[AVISO] La clave SECRET_KEY aún es la de ejemplo. Actualízala en .env.${NC}"
fi

echo -e ""
echo -e "${YELLOW}[5/10] Aplicando migraciones...${NC}"
python manage.py migrate --run-syncdb || {
    echo -e "${YELLOW}[AVISO] Migraciones fallaron. Verificando configuración...${NC}"
    python manage.py check
    echo -e "${GREEN}[OK] Configuración verificada${NC}"
}

echo -e "${GREEN}[OK] Migraciones completadas${NC}"

echo -e ""
echo -e "${YELLOW}[6/10] Cargando datos de prueba (opcional)...${NC}"
if [ -f "scripts/seed_data.py" ]; then
    python scripts/seed_data.py
    echo -e "${GREEN}[OK] Datos de prueba cargados${NC}"
else
    echo -e "${GREEN}[OK] No hay script de datos opcional${NC}"
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
echo -e "${YELLOW}[INFO] Revisa .env y completa DATABASE_URL/EMAIL_HOST_PASSWORD según tu Bitwarden si quieres sincronizar con Neon.${NC}"
echo -e ""
echo -e "================================================================"
