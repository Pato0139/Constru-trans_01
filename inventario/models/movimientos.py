"""
Movimientos de inventario (Kardex).
"""

from django.conf import settings
from django.db import models
from django.utils.timezone import now

from usuarios.models import MaterialConstruccion


class MovimientoInventario(models.Model):
    TIPOS = [("entrada", "Entrada"), ("salida", "Salida")]

    id_movimiento = models.AutoField(primary_key=True)
    material = models.ForeignKey(
        MaterialConstruccion, on_delete=models.PROTECT, related_name="movimientos", db_column="cod_material"
    )
    tipo_movimiento = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.PositiveIntegerField()
    fecha_movimiento = models.DateTimeField(default=now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="movimientos")

    # Campos fuera del MER pero útiles
    compra = models.ForeignKey(
        "compras.Compra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos",
    )
    pedido = models.ForeignKey(
        "ordenes.Pedido",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos",
    )
    observacion = models.TextField(blank=True)
    sincronizado = models.BooleanField(default=False)
    fecha = models.DateTimeField(default=now, blank=True, null=True)

    class Meta:
        ordering = ["-fecha_movimiento"]
        db_table = "movimiento_inventario"
        indexes = [
            models.Index(fields=["material", "fecha_movimiento"]),
            models.Index(fields=["tipo_movimiento"]),
        ]

    def __str__(self):
        return f"{self.tipo_movimiento.upper()}: {self.cantidad} de {self.material.nombre}"

    @property
    def id(self):
        return self.id_movimiento

    def save(self, *args, **kwargs):
        if self.fecha is None and self.fecha_movimiento:
            self.fecha = self.fecha_movimiento
        super().save(*args, **kwargs)
