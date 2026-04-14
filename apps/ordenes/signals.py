from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DetalleOrden

@receiver(post_save, sender=DetalleOrden)
def descontar_stock_detalle(sender, instance, created, **kwargs):
    if created:
        material = instance.material
        material.stock_actual -= instance.cantidad
        material.save()
