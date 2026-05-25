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
echo -e "${YELLOW}[1/10] Verificando Python...${NC}"
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
echo -e "${YELLOW}[2/10] Creando entorno virtual...${NC}"
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
echo -e "${YELLOW}[3/10] Instalando dependencias...${NC}"
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo -e "${RED}[ERROR] Fallo al instalar dependencias${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Dependencias instaladas${NC}"

# Paso 4: Clonar repositorio Neon para obtener credenciales
echo -e ""
echo -e "${YELLOW}[4/10] Obteniendo credenciales de Neon...${NC}"
neonRepoPath="Neon"
if [ -d "$neonRepoPath" ]; then
    rm -rf "$neonRepoPath"
fi
if git clone https://github.com/Pato0139/Neon.git "$neonRepoPath"; then
    echo -e "${GREEN}[OK] Repositorio Neon clonado${NC}"
else
    echo -e "${YELLOW}[ADVERTENCIA] No se pudo clonar el repositorio Neon. Continuando en modo local...${NC}"
fi

# Paso 5: Configurar .env con credenciales de Neon
echo -e ""
echo -e "${YELLOW}[5/10] Configurando archivo .env...${NC}"
if [ ! -f ".env" ]; then
    if [ -f "$neonRepoPath/.env.example" ]; then
        cp "$neonRepoPath/.env.example" ".env"
        echo -e "${GREEN}[OK] Archivo .env creado desde Neon${NC}"
        
        # Generar SECRET_KEY aleatorio
        SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
        sed -i.bak "s|SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres|SECRET_KEY=$SECRET_KEY|" .env && rm -f .env.bak
        echo -e "${GREEN}[OK] SECRET_KEY generado${NC}"
    else
        cp .env.example .env
        echo -e "${GREEN}[OK] Archivo .env creado desde .env.example${NC}"
        
        # Generar SECRET_KEY aleatorio
        SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
        sed -i.bak "s|SECRET_KEY=cambia-esto-por-una-clave-aleatoria-de-50-caracteres|SECRET_KEY=$SECRET_KEY|" .env && rm -f .env.bak
        echo -e "${GREEN}[OK] SECRET_KEY generado${NC}"
    fi
else
    echo -e "${GREEN}[OK] Archivo .env ya existe${NC}"
fi

# Paso 6: Eliminar repositorio Neon
echo -e ""
echo -e "${YELLOW}[6/10] Eliminando repositorio Neon...${NC}"
if [ -d "$neonRepoPath" ]; then
    rm -rf "$neonRepoPath"
    echo -e "${GREEN}[OK] Repositorio Neon eliminado${NC}"
fi

# Paso 7: Aplicar migraciones
echo -e ""
echo -e "${YELLOW}[7/10] Aplicando migraciones...${NC}"
python manage.py migrate --run-syncdb
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}[AVISO] Verificando configuracion...${NC}"
    python manage.py check
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] Problema con la configuracion${NC}"
    else
        echo -e "${GREEN}[OK] Configuracion verificada${NC}"
    fi
else
    echo -e "${GREEN}[OK] Migraciones aplicadas${NC}"
fi

# Paso 8: Cargar datos de prueba (opcional)
echo -e ""
echo -e "${YELLOW}[8/10] Cargando datos de prueba (opcional)...${NC}"
seedScript="scripts/seed_data.py"
if [ -f "$seedScript" ]; then
    python "$seedScript"
    echo -e "${GREEN}[OK] Datos de prueba cargados${NC}"
else
    echo -e "${GREEN}[OK] Script de datos no encontrado${NC}"
fi

# Paso 9: Final
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
