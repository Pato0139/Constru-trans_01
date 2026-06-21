import os
import sys
from pathlib import Path

# Añadir el directorio raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# --- CONFIGURACIÓN ---
IGNORE_DIRS = [".venv", "venv", "env", ".git", ".idea", "node_modules"]
DB_FILE = "db.sqlite3"


def buscar_archivos_migracion(base_path, ignore_dirs):
    """Busca recursivamente archivos de migración que no sean __init__.py"""
    migraciones = []
    for root, dirs, files in os.walk(base_path):
        # Ignorar carpetas no deseadas para no tocar paquetes instalados
        for d in list(dirs):
            if d in ignore_dirs:
                dirs.remove(d)

        # Solo buscar dentro de carpetas 'migrations'
        if "migrations" in root:
            for file in files:
                # Seleccionar archivos de migración (ej. 0001_initial.py)
                # IMPORTANTE: No borrar __init__.py
                if file.startswith("000") and file.endswith(".py"):
                    migraciones.append(Path(root) / file)
    return migraciones


def limpiar_proyecto():
    """Función principal para el reseteo de la base de datos y migraciones"""
    print("\n" + "=" * 60)
    print("  HERRAMIENTA DE RESETEO: MIGRACIONES Y BASE DE DATOS")
    print("=" * 60)
    print(f"[*] Trabajando en: {BASE_DIR}")
    print(f"[*] Ignorando entornos virtuales y carpetas de control: {IGNORE_DIRS}")

    # 1. Identificar archivos
    archivos_migracion = buscar_archivos_migracion(BASE_DIR, IGNORE_DIRS)
    db_path = BASE_DIR / DB_FILE
    db_existe = db_path.exists()

    # 2. Resumen de hallazgos
    if not archivos_migracion and not db_existe:
        print("\n[✓] El proyecto ya está limpio. No hay nada que borrar.")
        return

    print(f"\n[!] Se encontraron {len(archivos_migracion)} archivos de migración:")
    for arch in archivos_migracion:
        print(f"    - {arch}")

    if db_existe:
        print(f"\n[!] Se encontró la base de datos: {DB_FILE}")
    else:
        print(f"\n[i] No se encontró la base de datos '{DB_FILE}'.")

    # 3. No confirmation needed for auto-clean
    print("\n[*] Iniciando limpieza (auto-confirm)...")

    # Borrar archivos de migración
    for arch in archivos_migracion:
        try:
            arch.unlink()
            print(f"    [OK] Borrado: {arch}")
        except Exception as e:
            print(f"    [ERROR] No se pudo borrar {arch}: {e}")

    # Borrar base de datos
    if db_existe:
        try:
            db_path.unlink()
            print(f"    [OK] Borrado: {DB_FILE}")
        except Exception as e:
            print(f"    [ERROR] No se pudo borrar {DB_FILE}: {e}")

    print("\n✅ ¡Limpieza completada exitosamente!")
    print("[i] Ahora puedes ejecutar: python manage.py makemigrations y python manage.py migrate")


if __name__ == "__main__":
    limpiar_proyecto()
