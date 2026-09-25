from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import MaterialConstruccion, HistorialPrecioMaterial


@receiver(pre_save, sender=MaterialConstruccion)
def registrar_cambio_precio(sender, instance, **kwargs):
    if instance.pk:
        try:
            material_anterior = MaterialConstruccion.objects.get(pk=instance.pk)
            if material_anterior.precio_referencia != instance.precio_referencia:
                HistorialPrecioMaterial.objects.create(
                    material=instance,
                    precio_anterior=material_anterior.precio_referencia,
                    precio_nuevo=instance.precio_referencia,
                    observaciones=f"Cambio de precio desde {material_anterior.precio_referencia} hasta {instance.precio_referencia}"
                )
        except MaterialConstruccion.DoesNotExist:
            pass
