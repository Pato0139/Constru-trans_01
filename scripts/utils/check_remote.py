import os
import sys

import django

# Añadir el directorio del proyecto al path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.conf import settings
from django.db import connections

from core.db_preference import debe_usar_bd_remota, invalidate_connection_cache
from core.utils import conexion_remota_disponible, conexion_remota_disponible_cached

print("=" * 60)
print("VERIFICANDO CONEXIÓN REMOTA")
print("=" * 60)

print(f"\n1. 'remota' en settings.DATABASES: {'✅' if 'remota' in settings.DATABASES else '❌'}")

print("\n2. Limpiando caché...")
invalidate_connection_cache()
conexion_remota_disponible_cached.cache_clear()
print("   Caché limpiada.")

print("\n3. Probando conexión...")
try:
    connections["remota"].ensure_connection()
    print("   ✅ CONEXIÓN A LA BD REMOTA EXITOSA!")
except Exception as e:
    print(f"   ❌ ERROR AL CONECTAR: {type(e).__name__}: {e}")

print(f"\n4. conexion_remota_disponible(): {conexion_remota_disponible()}")
print(f"5. debe_usar_bd_remota(): {debe_usar_bd_remota()}")
print("\n✅ Todo está listo! El sistema debería usar el modo remoto.")
print("=" * 60)
