from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import DetalleOrden, Entrega, Orden

@receiver(post_save, sender=DetalleOrden)
def descontar_stock_detalle(sender, instance, created, **kwargs):
    # La lógica de descuento ahora se maneja directamente en la vista
    # para asegurar atomicidad y registrar el movimiento de inventario correctamente.
    pass

@receiver(post_save, sender=Entrega)
def actualizar_estado_orden(sender, instance, created, **kwargs):
    """Actualiza el estado de la orden solo cuando la entrega cambia a 'entregado'"""
    if instance.estado == 'entregado':
        pedido = instance.pedido
        if pedido.estado != Orden.ENTREGADO:
            pedido.estado = Orden.ENTREGADO
            pedido.fecha_entrega_real = timezone.now()
            pedido.save()
            
    elif instance.estado == 'en_ruta':
        pedido = instance.pedido
        if pedido.estado != Orden.EN_RUTA:
            pedido.estado = Orden.EN_RUTA
            pedido.save()
