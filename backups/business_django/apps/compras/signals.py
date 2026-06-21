from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DetalleCompra


@receiver(post_save, sender=DetalleCompra)
def actualizar_total_compra(sender, instance, created, **kwargs):
    instance.compra.calcular_total()
