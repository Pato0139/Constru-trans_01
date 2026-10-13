#!/usr/bin/env bash
# ============================================================
#  CONSTRU-TRANS - Instalador para macOS / Linux
#  Uso:  bash setup/setup_macos_linux.sh [opciones]
#    --dev                 instala tambien requirements/dev.txt
#    --seed                carga datos de prueba al finalizar
#    --reset-db            aparta una db.sqlite3 rota y crea una limpia
#    --no-fetch-credentials no intenta usar el repositorio compartido de credenciales
#                           (por defecto SI se intenta, como hacia el instalador original)
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
CYAN='\033[0;36m'; GRAY='\033[0;37m'; WHITE='\033[1;37m'; NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

INSTALAR_DEV=false; CARGAR_SEED=false; RESET_DB=false; FETCH_CREDENTIALS=true
for arg in "$@"; do
    case "$arg" in
        --dev) INSTALAR_DEV=true ;;
        --seed) CARGAR_SEED=true ;;
        --reset-db) RESET_DB=true ;;
        --fetch-credentials) FETCH_CREDENTIALS=true ;;
        --no-fetch-credentials) FETCH_CREDENTIALS=false ;;
        -h|--help)
            sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) echo -e "${YELLOW}[AVISO] Opcion desconocida: $arg (se ignora)${NC}" ;;
    esac
done

echo -e "${CYAN}================================================================"
echo -e "${BLUE}CONSTRU-TRANS - Instalacion automatica (macOS / Linux)"
echo -e "${CYAN}================================================================${NC}"
echo

# ---------- [1/6] Python ----------
echo -e "${BLUE}[1/6] Verificando Python...${NC}"
PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.13 python3.14 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1 \
        && "$cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
        PYTHON_CMD="$cmd"; break
    fi
done
if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}[ERROR] Se requiere Python 3.11 o superior (recomendado 3.12)."
    echo -e "${YELLOW}Descargalo en https://www.python.org/downloads/ y vuelve a ejecutar el setup.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] $("$PYTHON_CMD" --version)${NC}"

# ---------- [2/6] Entorno virtual ----------
echo
echo -e "${BLUE}[2/6] Preparando entorno virtual...${NC}"
PROJECT_PREFIX="$PROJECT_ROOT/"
VENV_DIR=""
VENV_PYTHON=""

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "${VIRTUAL_ENV}/bin/python" ]; then
    case "$VIRTUAL_ENV/" in
        "$PROJECT_PREFIX"*)
            VENV_DIR="$VIRTUAL_ENV"; VENV_PYTHON="$VIRTUAL_ENV/bin/python"
            echo -e "${GREEN}[OK] Se reutiliza el entorno activo: $VENV_DIR${NC}" ;;
    esac
fi

if [ -z "$VENV_PYTHON" ]; then
    for candidato in "$PROJECT_ROOT/.venv" "$PROJECT_ROOT/venv"; do
        if [ -x "$candidato/bin/python" ]; then
            VENV_DIR="$candidato"; VENV_PYTHON="$candidato/bin/python"
            echo -e "${GREEN}[OK] Se reutiliza el entorno existente: $VENV_DIR${NC}"; break
        fi
    done
fi

if [ -z "$VENV_PYTHON" ]; then
    for candidato in "$PROJECT_ROOT"/.venv-*; do
        [ -x "$candidato/bin/python" ] || continue
        VENV_DIR="$candidato"; VENV_PYTHON="$candidato/bin/python"
        echo -e "${GREEN}[OK] Se reutiliza el entorno existente: $VENV_DIR${NC}"; break
    done
fi

if [ -z "$VENV_PYTHON" ]; then
    VENV_DIR="$PROJECT_ROOT/.venv"
    if [ -e "$VENV_DIR" ]; then
        echo -e "${RED}[ERROR] $VENV_DIR existe pero no contiene un Python valido."
        echo -e "${YELLOW}Renombralo o eliminalo y vuelve a ejecutar el setup. No se borro nada.${NC}"
        exit 1
    fi
    echo -e "${GRAY}[INFO] Creando $VENV_DIR ...${NC}"
    if ! "$PYTHON_CMD" -m venv "$VENV_DIR"; then
        echo -e "${RED}[ERROR] No se pudo crear el entorno virtual.${NC}"
        echo -e "${YELLOW}En Debian/Ubuntu instala el paquete: sudo apt install python3-venv${NC}"
        exit 1
    fi
    VENV_PYTHON="$VENV_DIR/bin/python"
    echo -e "${GREEN}[OK] Entorno creado${NC}"
fi

# ---------- [3/6] Dependencias ----------
echo
echo -e "${BLUE}[3/6] Instalando dependencias...${NC}"
"$VENV_PYTHON" -m pip install --upgrade pip >/dev/null
if ! "$VENV_PYTHON" -m pip install --prefer-binary -r "$PROJECT_ROOT/requirements.txt"; then
    echo -e "${RED}[ERROR] Fallo la instalacion de dependencias. Revisa tu conexion a Internet.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Dependencias instaladas${NC}"

if [ "$INSTALAR_DEV" = true ]; then
    echo -e "${GRAY}[INFO] Instalando herramientas de desarrollo...${NC}"
    "$VENV_PYTHON" -m pip install --prefer-binary -r "$PROJECT_ROOT/requirements/dev.txt" || \
        echo -e "${YELLOW}[AVISO] Fallaron las dependencias de desarrollo; el proyecto sigue operativo.${NC}"
fi

# ---------- [4/6] Archivo .env ----------
echo
echo -e "${BLUE}[4/6] Configurando el archivo .env...${NC}"
ENV_FILE="$PROJECT_ROOT/.env"

if [ "$FETCH_CREDENTIALS" = true ] && [ ! -f "$ENV_FILE" ] && command -v git >/dev/null 2>&1; then
    echo -e "${GRAY}[INFO] Intentando obtener credenciales compartidas...${NC}"
    TEMP_DIR="$PROJECT_ROOT/temp_neon_repo"
    rm -rf "$TEMP_DIR"
    if GIT_TERMINAL_PROMPT=0 git clone --depth 1 https://github.com/Pato0139/Neon.git "$TEMP_DIR" >/dev/null 2>&1; then
        if [ -f "$TEMP_DIR/.env" ]; then
            cp "$TEMP_DIR/.env" "$ENV_FILE"
            echo -e "${GREEN}[OK] .env creado desde el repositorio de credenciales${NC}"
        elif [ -f "$TEMP_DIR/.env.example" ]; then
            cp "$TEMP_DIR/.env.example" "$ENV_FILE"
            echo -e "${GREEN}[OK] .env creado desde el repositorio de credenciales${NC}"
        else
            echo -e "${YELLOW}[AVISO] El repositorio no traia archivo de configuracion.${NC}"
        fi
    else
        echo -e "${YELLOW}[AVISO] No se pudo clonar (repo privado o sin acceso). Se usara la plantilla local.${NC}"
    fi
    rm -rf "$TEMP_DIR"
fi

if [ ! -f "$ENV_FILE" ]; then
    [ -f "$PROJECT_ROOT/.env.example" ] && cp "$PROJECT_ROOT/.env.example" "$ENV_FILE" || : > "$ENV_FILE"
    echo -e "${GREEN}[OK] .env creado desde .env.example${NC}"
else
    echo -e "${GREEN}[OK] Se conserva el .env existente${NC}"
fi

# Garantiza una SECRET_KEY estable y valida (no se regenera en cada arranque).
SECRET_OK=$("$VENV_PYTHON" - "$ENV_FILE" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); texto = p.read_text(encoding="utf-8-sig") if p.exists() else ""
mala = {"", "cambiar", "cambia-esto-por-una-clave-aleatoria-de-50-caracteres",
        "change-me", "changeme", "secret-key", "example-secret-key"}
for linea in texto.splitlines():
    clave, sep, valor = linea.partition("=")
    if sep and clave.strip() == "SECRET_KEY":
        v = valor.strip().strip("'\"")
        print("ok" if len(v) >= 32 and v.lower() not in mala else "no"); raise SystemExit
print("no")
PY
)
if [ "$SECRET_OK" != "ok" ]; then
    NUEVA_CLAVE=$("$VENV_PYTHON" -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    "$VENV_PYTHON" - "$ENV_FILE" "$NUEVA_CLAVE" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1]); clave = sys.argv[2]
lineas = p.read_text(encoding="utf-8-sig").splitlines() if p.exists() else []
salida, puesta = [], False
for linea in lineas:
    if linea.partition("=")[0].strip() == "SECRET_KEY":
        salida.append(f"SECRET_KEY={clave}"); puesta = True
    else:
        salida.append(linea)
if not puesta:
    salida.append(f"SECRET_KEY={clave}")
p.write_text("\n".join(salida) + "\n", encoding="utf-8")
PY
    echo -e "${GREEN}[OK] SECRET_KEY fija generada y guardada en .env${NC}"
else
    echo -e "${GREEN}[OK] SECRET_KEY valida encontrada en .env${NC}"
fi

# ---------- [5/6] Base de datos ----------
echo
echo -e "${BLUE}[5/6] Preparando la base de datos local...${NC}"
if [ "$RESET_DB" = true ] && [ -f "$PROJECT_ROOT/db.sqlite3" ]; then
    RESPALDO="$PROJECT_ROOT/db.sqlite3.broken-$(date +%Y%m%d-%H%M%S)"
    mv "$PROJECT_ROOT/db.sqlite3" "$RESPALDO"
    echo -e "${YELLOW}[INFO] Base anterior apartada en: $(basename "$RESPALDO")${NC}"
fi

echo -e "${GRAY}[INFO] Verificando la configuracion de Django...${NC}"
if ! DATABASE_URL="" "$VENV_PYTHON" manage.py check; then
    echo -e "${RED}[ERROR] La configuracion de Django no es valida.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Configuracion correcta${NC}"

echo -e "${GRAY}[INFO] Aplicando migraciones...${NC}"
set +e
SALIDA_MIGRATE=$(DATABASE_URL="" "$VENV_PYTHON" manage.py migrate --noinput 2>&1)
CODIGO_MIGRATE=$?
set -e
TIENE_REMOTA=false
if grep -qE '^DATABASE_URL=.+' "$ENV_FILE" 2>/dev/null; then TIENE_REMOTA=true; fi

if [ $CODIGO_MIGRATE -ne 0 ]; then
    echo "$SALIDA_MIGRATE" | tail -4
    echo
    if echo "$SALIDA_MIGRATE" | grep -q "already exists"; then
        echo -e "${YELLOW}[AVISO] La base local quedo a medias entre dos versiones del esquema.${NC}"
        echo -e "${YELLOW}Solucion: bash setup/setup_macos_linux.sh --reset-db${NC}"
        echo -e "${GRAY}(No se borra nada: la base actual se aparta como db.sqlite3.broken-<fecha>)${NC}"
    else
        echo -e "${RED}[ERROR] Las migraciones de la base local fallaron.${NC}"
    fi

    if [ "$TIENE_REMOTA" = true ]; then
        echo -e "${GRAY}[INFO] Como hay DATABASE_URL configurada, el proyecto usara la base compartida.${NC}"
    elif [ -f "$PROJECT_ROOT/db.sqlite3" ]; then
        echo -e "${YELLOW}[AVISO] Ya existia una db.sqlite3: se conserva y el setup continua con ella.${NC}"
    else
        echo -e "${RED}No hay base utilizable. Revisa el error anterior o ejecuta con --reset-db.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}[OK] Base de datos local lista${NC}"
fi

if [ -n "$(grep -E '^DATABASE_URL=.+' "$ENV_FILE" || true)" ]; then
    echo -e "${GRAY}[INFO] DATABASE_URL definida: se aplicaran tambien las migraciones remotas.${NC}"
    if DATABASE_URL="" "$VENV_PYTHON" manage.py migrate --database=remota --noinput 2>/dev/null; then
        echo -e "${GREEN}[OK] Base remota actualizada${NC}"
    else
        echo -e "${YELLOW}[AVISO] No se pudo migrar la base remota; el trabajo local continua normal.${NC}"
    fi
fi

# ---------- [6/6] Datos de prueba y cierre ----------
if [ "$CARGAR_SEED" = true ]; then
    echo
    echo -e "${BLUE}[6/6] Cargando datos de prueba...${NC}"
    DATABASE_URL="" "$VENV_PYTHON" manage.py poblar_todo || \
        echo -e "${YELLOW}[AVISO] No se pudieron cargar los datos de prueba.${NC}"
fi

echo
echo -e "${CYAN}================================================================"
echo -e "${GREEN}Setup COMPLETO"
echo -e "${CYAN}================================================================${NC}"
echo -e "${BLUE}Para iniciar el servidor:"
echo -e "${WHITE}  $VENV_PYTHON manage.py runserver"
echo -e "${GRAY}  Abre http://127.0.0.1:8000/ en el navegador"
echo -e "${BLUE}Para ejecutar las pruebas:"
echo -e "${WHITE}  $VENV_PYTHON manage.py test${NC}"
echo
