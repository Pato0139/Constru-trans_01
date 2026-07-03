from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import MaterialConstruccion, HistorialPrecioMaterial


@receiver(pre_save, sender=MaterialConstruccion)
def registrar_cambio_precio(sender, instance, **kwargs):
    """
    Registra el cambio de precio de un material en el historial.
    """
    if instance.pk:
        try:
            material_anterior = MaterialConstruccion.objects.get(pk=instance.pk)
            if material_anterior.precio_referencia != instance.precio_referencia:
                # El precio ha cambiado, registramos en el historial
                HistorialPrecioMaterial.objects.create(
                    material=instance,
                    precio_anterior=material_anterior.precio_referencia,
                    precio_nuevo=instance.precio_referencia,
                    observaciones=f"Cambio de precio desde {material_anterior.precio_referencia} hasta {instance.precio_referencia}"
                )
        except MaterialConstruccion.DoesNotExist:
            pass
