from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Compra
from apps.usuarios.models import Stock
from apps.inventario.models import MovimientoInventario
from django.db import transaction
from django.db.models import F

@receiver(pre_save, sender=Compra)
def capturar_estado_anterior(sender, instance, **kwargs):
    if instance.pk:
        instance._estado_anterior = Compra.objects.get(pk=instance.pk).estado
    else:
        instance._estado_anterior = None

@receiver(post_save, sender=Compra)
def actualizar_stock_al_recibir(sender, instance, created, **kwargs):
    # Si el estado cambió a 'recibida', actualizar stock para todos los detalles
    estado_anterior = getattr(instance, '_estado_anterior', None)
    
    if instance.estado == Compra.RECIBIDA and estado_anterior != Compra.RECIBIDA:
        with transaction.atomic():
            for detalle in instance.detalles.all():
                stock_obj, created_stock = Stock.objects.select_for_update().get_or_create(material=detalle.material)
                stock_obj.cantidad = F('cantidad') + detalle.cantidad
                stock_obj.save()
                
                # Registrar movimiento de inventario
                MovimientoInventario.objects.create(
                    material=detalle.material,
                    tipo='entrada',
                    cantidad=detalle.cantidad,
                    motivo=f"Compra recibida {instance.numero_orden}",
                    referencia_id=instance.id
                )
