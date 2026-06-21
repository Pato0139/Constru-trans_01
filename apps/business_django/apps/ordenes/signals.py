from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.usuarios.models import ConductorVehiculo

from .models import DetallePedido, Entrega


@receiver(post_save, sender=DetallePedido)
def actualizar_total_pedido(sender, instance, created, **kwargs):
    instance.pedido.calcular_total()


@receiver(post_save, sender=ConductorVehiculo)
def actualizar_estado_vehiculo_con_asignacion(sender, instance, created, **kwargs):
    """Actualizar estado del vehículo cuando se asigna/unasigna un conductor"""
    if instance.fecha_fin is None:
        # Asignación activa → estado "asignado"
        instance.vehiculo.estado = "asignado"
    else:
        # Asignación terminada → ver si hay otras asignaciones activas
        otras_asignaciones = (
            ConductorVehiculo.objects.filter(vehiculo=instance.vehiculo, fecha_fin__isnull=True)
            .exclude(pk=instance.pk)
            .exists()
        )
        instance.vehiculo.estado = "asignado" if otras_asignaciones else "disponible"
    instance.vehiculo.save()


@receiver(post_delete, sender=ConductorVehiculo)
def actualizar_estado_vehiculo_sin_asignacion(sender, instance, **kwargs):
    """Actualizar estado del vehículo cuando se elimina una asignación"""
    # Ver si hay otras asignaciones activas
    asignaciones_restantes = ConductorVehiculo.objects.filter(
        vehiculo=instance.vehiculo, fecha_fin__isnull=True
    ).exists()
    instance.vehiculo.estado = "asignado" if asignaciones_restantes else "disponible"
    instance.vehiculo.save()


@receiver(post_save, sender=Entrega)
def actualizar_estado_vehiculo_entrega(sender, instance, created, **kwargs):
    """Actualizar estado del vehículo cuando cambia el estado de una entrega"""
    if instance.vehiculo:
        # Ver si hay entregas activas para este vehículo
        entregas_activas = Entrega.objects.filter(
            vehiculo=instance.vehiculo, estado__in=["pendiente", "en_ruta"]
        ).exists()

        # Ver si hay conductor asignado
        conductor_asignado = ConductorVehiculo.objects.filter(
            vehiculo=instance.vehiculo, fecha_fin__isnull=True
        ).exists()

        if entregas_activas or conductor_asignado:
            instance.vehiculo.estado = "asignado"
        else:
            instance.vehiculo.estado = "disponible"
        instance.vehiculo.save()
