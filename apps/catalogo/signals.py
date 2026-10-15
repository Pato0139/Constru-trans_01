from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import HistorialPrecioMaterial, MaterialConstruccion, Stock


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


@receiver(post_save, sender=Stock)
def sincronizar_stock_producto(sender, instance, **kwargs):
    """Mantiene la columna 'stock' del producto igualada con su registro
    de Stock (movimientos de inventario, edición de stock, etc.)."""
    db = instance._state.db or "default"
    cantidad_actual = sender.objects.using(db).values_list(
        "cantidad_actual", flat=True
    ).get(pk=instance.pk)
    MaterialConstruccion.objects.using(db).filter(pk=instance.material_id).update(
        stock=cantidad_actual
    )
