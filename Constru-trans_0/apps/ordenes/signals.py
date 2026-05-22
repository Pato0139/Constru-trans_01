from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Pedido, DetallePedido


@receiver(post_save, sender=DetallePedido)
def actualizar_total_pedido(sender, instance, created, **kwargs):
    instance.pedido.calcular_total()
