from django.db import models
from django.utils import timezone

class Entrega(models.Model):

    class EstadoEntrega(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        EN_CAMINO = 'en_camino', 'En camino'
        ENTREGADO = 'entregado', 'Entregado'

    conductor = models.CharField(max_length=100, blank=True)
    vehiculo = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoEntrega.choices,
        default=EstadoEntrega.PENDIENTE,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_ultimo_cambio_estado = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Entrega #{self.id} - {self.estado}"


class HistorialEstadoEntrega(models.Model):
    entrega = models.ForeignKey(
        Entrega,
        on_delete=models.CASCADE,
        related_name='historial'
    )
    estado_anterior = models.CharField(max_length=20)
    estado_nuevo = models.CharField(max_length=20)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    conductor = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Entrega #{self.entrega.id}: {self.estado_anterior} → {self.estado_nuevo}"