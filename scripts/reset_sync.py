
import os
import sys
import django
from pathlib import Path

# Añadir el directorio raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.usuarios.models import Usuario, Material, Proveedor, Vehiculo
from apps.compras.models import Compra
from apps.ordenes.models import Orden
from apps.inventario.models import MovimientoInventario

print("Reseteando flags de sincronización...")
Usuario.objects.all().update(sincronizado=False)
Material.objects.all().update(sincronizado=False)
Proveedor.objects.all().update(sincronizado=False)
Vehiculo.objects.all().update(sincronizado=False)
Compra.objects.all().update(sincronizado=False)
Orden.objects.all().update(sincronizado=False)
MovimientoInventario.objects.all().update(sincronizado=False)
print("¡Listo! Todos los registros marcados para re-sincronizar.")
