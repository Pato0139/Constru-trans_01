import os
import sys
import django
from django.db import connections
from pathlib import Path

# Añadir el directorio raíz al sys.path para que Django pueda encontrar los módulos
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def check_tables():
    print("--- LOCAL (SQLite) ---")
    with connections['default'].cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print([row[0] for row in cursor.fetchall()])
    
    print("\n--- REMOTE (Neon/Postgres) ---")
    with connections['remota'].cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
        tables = [row[0] for row in cursor.fetchall()]
        print(tables)
        if 'historial_actividad' in tables:
            print("SUCCESS: historial_actividad found on remote")
        else:
            print("FAILURE: historial_actividad NOT found on remote")

if __name__ == "__main__":
    check_tables()
