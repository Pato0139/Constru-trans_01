from django.db import transaction
from django.db.models import F
from apps.usuarios.models import Stock
from apps.inventario.models import MovimientoInventario
from apps.historial.utils import registrar_actividad

def revertir_stock_pedido(orden, usuario, motivo_prefijo="Cancelación"):
    """
    Revierte el stock de una orden y registra los movimientos de entrada.
    Debe llamarse dentro de un bloque transaction.atomic() si se usa con otras operaciones.
    """
    for detalle in orden.detalles.all():
        # Obtenemos o creamos el stock para el material
        stock_obj, created = Stock.objects.select_for_update().get_or_create(
            material=detalle.material,
            defaults={'cantidad': 0}
        )
        stock_obj.cantidad = F('cantidad') + detalle.cantidad
        stock_obj.save()
        
        # Registrar movimiento de re-entrada
        MovimientoInventario.objects.create(
            material=detalle.material,
            tipo='entrada',
            cantidad=detalle.cantidad,
            motivo=f"{motivo_prefijo} pedido #{orden.id}",
            referencia_id=orden.id,
            usuario=usuario
        )

def liberar_vehiculo_pedido(orden):
    """
    Libera el vehículo asociado a la entrega de una orden si existe.
    """
    entrega = orden.entregas.first()
    if entrega and entrega.vehiculo:
        vehiculo = entrega.vehiculo
        vehiculo.estado = 'disponible'
        vehiculo.save()
        return vehiculo
    return None
