import logging

from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import HistorialPrecioMaterial, MaterialConstruccion, Stock

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=MaterialConstruccion)
def registrar_cambio_precio(sender, instance, using=None, **kwargs):
    if instance.pk:
        db = using or instance._state.db or "default"
        try:
            material_anterior = MaterialConstruccion.objects.using(db).get(pk=instance.pk)
            if material_anterior.precio_referencia != instance.precio_referencia:
                HistorialPrecioMaterial.objects.using(db).create(
                    material=instance,
                    precio_anterior=material_anterior.precio_referencia,
                    precio_nuevo=instance.precio_referencia,
                    observaciones=f"Cambio de precio desde {material_anterior.precio_referencia} hasta {instance.precio_referencia}",
                )
        except MaterialConstruccion.DoesNotExist:
            pass


@receiver(post_save, sender=Stock)
def sincronizar_stock_producto(sender, instance, raw=False, using=None, **kwargs):
    """Mantiene la columna 'stock' del producto igualada con su registro
    de Stock (movimientos de inventario, edición de stock, etc.) y evalúa alertas."""
    if raw:
        return
    db = using or instance._state.db or "default"
    cantidad_actual = sender.objects.using(db).values_list(
        "cantidad_actual", flat=True
    ).get(pk=instance.pk)
    MaterialConstruccion.objects.using(db).filter(pk=instance.material_id).update(
        stock=cantidad_actual
    )

    def evaluar_alerta():
        try:
            stock_actual = (
                Stock.objects.using(db)
                .select_related("material__unidad_medida", "material__catalogo")
                .get(pk=instance.pk)
            )
            from .services.kardex import evaluar_y_notificar_stock_bajo

            evaluar_y_notificar_stock_bajo(
                stock_actual.material,
                cantidad_actual=stock_actual.cantidad_actual,
                umbral=stock_actual.stock_minimo,
            )
        except Exception:
            logger.exception(
                "No se pudo evaluar la alerta de stock para el material %s",
                instance.material_id,
            )

    transaction.on_commit(evaluar_alerta, using=db)
