#!/usr/bin/env python
"""
Script to fix common Django migration issues.
"""
import os
import sys
import shutil
from pathlib import Path

# Add the project root to the path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.development")
import django
django.setup()

from django.conf import settings


def fix_migration_issues():
    """
    Fix common migration issues:
    1. Delete the SQLite database file (if using default)
    2. Delete all migration files except __init__.py
    3. Recreate migrations and apply them
    """
    print("=" * 60)
    print("Django Migration Fixer")
    print("=" * 60)
    
    # Step 1: Delete the SQLite database file
    db_path = settings.DATABASES["default"]["NAME"]
    if isinstance(db_path, Path) and db_path.exists():
        print(f"\nDeleting database file: {db_path}")
        db_path.unlink()
    elif isinstance(db_path, str) and os.path.exists(db_path):
        print(f"\nDeleting database file: {db_path}")
        os.remove(db_path)
    
    # Step 2: Recreate migrations for all apps
    print("\nRecreating migrations for all local apps...")
    local_apps = [
        "usuarios",
        "clientes",
        "inventario",
        "compras",
        "ordenes",
        "gestion_pedidos",
        "facturacion",
        "pagos",
        "reportes",
        "inicio",
        "historial",
        "transporte",
        "licensing",
        "ia",
    ]
    
    for app in local_apps:
        app_dir = BASE_DIR / "apps" / app
        migrations_dir = app_dir / "migrations"
        
        if migrations_dir.exists():
            print(f"\nProcessing {app}...")
            # Delete all migration files except __init__.py
            for migration_file in migrations_dir.glob("*.py"):
                if migration_file.name != "__init__.py":
                    print(f"  Deleting: {migration_file.name}")
                    migration_file.unlink()
    
    # Step 3: Run makemigrations and migrate
    print("\n" + "=" * 60)
    print("Now run these commands manually:")
    print("  python manage.py makemigrations")
    print("  python manage.py migrate")
    print("=" * 60)


if __name__ == "__main__":
    fix_migration_issues()