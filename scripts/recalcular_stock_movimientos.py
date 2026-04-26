import os
import sys
import django
from pathlib import Path

# Añadir el directorio raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.usuarios.models import Material, Stock
from apps.inventario.models import MovimientoInventario
from django.db.models import Sum

def recalcular_stock():
    print("Iniciando sincronización de stock...")

    # 1. CORRECCIÓN: Usamos 'movimientos' (plural) que es el related_name real
    materiales_con_movimientos = Material.objects.filter(
        movimientos__isnull=False
    ).distinct()

    contador = 0
    for material in materiales_con_movimientos:
        # 2. Calcular la suma de entradas y salidas
        total_stock = MovimientoInventario.objects.filter(
            material=material
        ).aggregate(
            total=Sum('cantidad')
        )['total'] or 0

        # 3. Crear o actualizar el registro en Stock
        # CORRECCIÓN: Agregamos ubicación por defecto para evitar errores de BD
        stock_obj, created = Stock.objects.get_or_create(
            material=material,
            defaults={'ubicacion': 'Almacén General', 'cantidad': 0}
        )
        
        # Si el stock calculado es diferente al que hay en BD, lo actualizamos
        if stock_obj.cantidad != total_stock:
            stock_obj.cantidad = total_stock
            stock_obj.save()
            print(f"Actualizado stock para {material.nombre}: {total_stock}")
            contador += 1
        elif created:
            print(f"Creado stock para {material.nombre}: {total_stock}")
            contador += 1

    print(f"Proceso terminado. Se procesaron {contador} materiales.")
    print("Verificando datos...")
    for s in Stock.objects.all():
        print(f"- {s.material.nombre}: {s.cantidad} unidades en {s.ubicacion}")

if __name__ == '__main__':
    recalcular_stock()
