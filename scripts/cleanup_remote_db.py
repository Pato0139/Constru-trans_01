
import os
import sys
import django
from pathlib import Path
from django.db import connections

# Añadir el directorio raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def cleanup_remote_db():
    print("--- Iniciando limpieza de tablas innecesarias en Neon (Remota) ---")
    
    # Lista de tablas que NO aportan nada o son temporales/basura
    tablas_a_borrar = [
        'django_session',      # Sesiones locales no sirven en la nube
        'django_migrations',   # La nube debe manejarse por esquema, no por historial local de migraciones
        'django_content_type', # Se regeneran automáticamente
    ]
    
    with connections['remota'].cursor() as cursor:
        for tabla in tablas_a_borrar:
            try:
                print(f"Intentando borrar tabla: {tabla}...")
                cursor.execute(f"DROP TABLE IF EXISTS {tabla} CASCADE;")
                print(f"  [OK] Tabla {tabla} eliminada.")
            except Exception as e:
                print(f"  [ERROR] No se pudo borrar {tabla}: {e}")

if __name__ == "__main__":
    cleanup_remote_db()
    print("--- Limpieza completada ---")
