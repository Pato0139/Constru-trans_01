"""
Script para configurar la conexión a PostgreSQL/Neon.
Ejecuta: python configurar_db.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
ENV_FILE = BASE_DIR / ".env"

def main():
    print("=" * 60)
    print("  Configuración de Base de Datos PostgreSQL/Neon")
    print("=" * 60)
    print()
    print("Ingresa tu DATABASE_URL de Neon (formato: postgresql://usuario:password@host:puerto/db)")
    print("La URL se guardará directamente en tu archivo .env")
    print()
    
    database_url = input("DATABASE_URL: ").strip()
    
    if not database_url:
        print("❌ No ingresaste ninguna URL. Cancelando.")
        sys.exit(1)
    
    if not database_url.startswith("postgresql://"):
        print("❌ La URL debe comenzar con 'postgresql://'")
        sys.exit(1)
    
    # Leer .env actual
    env_content = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    
    # Actualizar o agregar DATABASE_URL
    lines = env_content.splitlines()
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("DATABASE_URL="):
            new_lines.append(f"DATABASE_URL={database_url}")
            found = True
        else:
            new_lines.append(line)
    
    if not found:
        new_lines.append(f"DATABASE_URL={database_url}")
    
    ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    
    print()
    print("✅ DATABASE_URL guardada en .env")
    print()
    
    # Verificar conexión
    print("Verificando conexión...")
    os.environ["DATABASE_URL"] = database_url
    
    try:
        import django
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
        django.setup()
        
        from django.db import connections
        conn = connections["default"]
        conn.ensure_connection()
        print(f"✅ Conexión exitosa a PostgreSQL/Neon")
        print(f"   Versión: {conn.connection.server_version}")
        
        # Contar tablas
        with conn.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")
            count = cursor.fetchone()[0]
            print(f"   Tablas existentes: {count}")
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
