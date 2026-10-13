#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "CONSTRU-TRANS - Instalador para macOS/Linux"
echo

PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.13 python3.14 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1 \
        && "$cmd" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "[ERROR] Se requiere Python 3.11 o superior (se recomienda 3.12). Instálalo y vuelve a ejecutar el setup." >&2
    exit 1
fi
echo "[OK] Python seleccionado: $("$PYTHON_CMD" --version)"

VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
if [ -d "$VENV_DIR" ] && [ ! -x "$VENV_PYTHON" ]; then
    echo "[ERROR] El entorno .venv existe pero está incompleto. Elimínalo manualmente y vuelve a ejecutar el setup." >&2
    exit 1
fi
if [ ! -x "$VENV_PYTHON" ]; then
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

echo "[OK] Instalando dependencias de requirements.txt..."
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install --prefer-binary -r "$PROJECT_ROOT/requirements.txt"

if [ ! -f "$PROJECT_ROOT/.env" ]; then
    SECRET_KEY="$("$VENV_PYTHON" -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
    cat > "$PROJECT_ROOT/.env" <<EOF
DJANGO_ENV=development
SECRET_KEY=$SECRET_KEY
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
DATABASE_URL=
OPENWEATHER_API_KEY=
EOF
    echo "[OK] Se creó .env para desarrollo local."
else
    echo "[OK] Se conserva el .env existente."
fi

echo "[OK] Verificando configuración Django..."
DATABASE_URL="" "$VENV_PYTHON" manage.py check

echo "[OK] Aplicando migraciones a la base SQLite local..."
DATABASE_URL="" "$VENV_PYTHON" manage.py migrate --run-syncdb

echo
echo "Setup completado."
echo "Para iniciar el servidor:"
echo "  .venv/bin/python manage.py runserver"
