import os
import sys
import django
from django.db import connections
from pathlib import Path

# Añadir el directorio raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def cleanup():
    with connections['remota'].cursor() as cursor:
        print("Checking migration records on remote...")
        cursor.execute("SELECT name FROM django_migrations WHERE app='historial'")
        print(f"Records found: {cursor.fetchall()}")
        
        print("Dropping tables on remote...")
        cursor.execute("DROP TABLE IF EXISTS historial_historial CASCADE")
        cursor.execute("DROP TABLE IF EXISTS historial_actividad CASCADE")
        
        print("Cleaning up migration records on remote...")
        cursor.execute("DELETE FROM django_migrations WHERE app='historial'")
        
        print("Verifying cleanup...")
        cursor.execute("SELECT name FROM django_migrations WHERE app='historial'")
        print(f"Records remaining: {cursor.fetchall()}")
        print("Done.")

if __name__ == "__main__":
    cleanup()
