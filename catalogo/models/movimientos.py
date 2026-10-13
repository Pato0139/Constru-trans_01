from django.conf import settings
from django.db import models
from django.utils.timezone import now

from catalogo.models import MaterialConstruccion


class MovimientoInventario(models.Model):
    TIPOS = [("entrada", "Entrada"), ("salida", "Salida")]

    id_movimiento = models.AutoField(primary_key=True)
    material = models.ForeignKey(
        MaterialConstruccion,
        on_delete=models.PROTECT,
        related_name="movimientos",
        db_column="cod_material",
        null=True,
        blank=True,
    )
    material_codigo_original = models.IntegerField(null=True, blank=True, editable=False)
    tipo_movimiento = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.PositiveIntegerField()
    fecha_movimiento = models.DateTimeField(default=now)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="movimientos")

    compra = models.ForeignKey(
        "compras.Compra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos",
    )
    pedido = models.ForeignKey(
        "pedidos.Pedido",
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
        return f"{self.tipo_movimiento.upper()}: {self.cantidad} de {self.material_label}"

    @property
    def id(self):
        return self.id_movimiento

    @property
    def material_label(self):
        if self.material_id is not None:
            return self.material.nombre
        if self.material_codigo_original is not None:
            return f"Material no disponible (código {self.material_codigo_original})"
        return "Material no asignado"

    def save(self, *args, **kwargs):
        if self.fecha is None and self.fecha_movimiento:
            self.fecha = self.fecha_movimiento
        super().save(*args, **kwargs)
