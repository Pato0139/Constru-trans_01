from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Seguimiento


@receiver(post_save, sender=Seguimiento)
def actualizar_estado_novedad_al_crear_seguimiento(sender, instance, created, **kwargs):
    """Al crear un primer seguimiento, la novedad pasa de "abierta" a "en_atencion"."""
    if created:
        novedad = instance.novedad
        if novedad.estado == "abierta":
            novedad.estado = "en_atencion"
            novedad.save(update_fields=["estado"])
