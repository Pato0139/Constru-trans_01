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
echo -e "${YELLOW}[1/6] Verificando Python...${NC}"
if command -v python3 &amp;&gt; /dev/null; then
    PYTHON_CMD="python3"
    echo -e "${GREEN}[OK] Python encontrado: $($PYTHON_CMD --version)${NC}"
elif command -v python &amp;&gt; /dev/null; then
    PYTHON_CMD="python"
    echo -e "${GREEN}[OK] Python encontrado: $($PYTHON_CMD --version)${NC}"
else
    echo -e "${RED}[ERROR] Python no encontrado. Instala Python 3.11+${NC}"
    exit 1
fi

# Paso 2: Crear entorno virtual
echo -e ""
echo -e "${YELLOW}[2/6] Creando entorno virtual...${NC}"
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
echo -e "${YELLOW}[3/6] Instalando dependencias...${NC}"
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al instalar dependencias${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Dependencias instaladas${NC}"

# Paso 4: Verificar .env
echo -e ""
echo -e "${YELLOW}[4/6] Verificando archivo .env...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}[OK] Archivo .env creado${NC}"
else
    echo -e "${GREEN}[OK] Archivo .env ya existe${NC}"
fi

# Paso 5: Aplicar migraciones
echo -e ""
echo -e "${YELLOW}[5/6] Aplicando migraciones...${NC}"
python manage.py migrate
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al aplicar migraciones${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Migraciones aplicadas${NC}"

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
