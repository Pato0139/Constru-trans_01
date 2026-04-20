from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DetalleOrden
from django.db.models import F

@receiver(post_save, sender=DetalleOrden)
def descontar_stock_detalle(sender, instance, created, **kwargs):
    # La lógica de descuento ahora se maneja directamente en la vista
    # para asegurar atomicidad y registrar el movimiento de inventario correctamente.
    pass
