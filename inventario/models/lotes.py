"""
Lotes de material — fecha de vencimiento.
"""

from django.db import models
from django.utils import timezone

from usuarios.models import MaterialConstruccion


class LoteMaterial(models.Model):
    """Lote de material con fecha de vencimiento (para cemento, pintura, etc.)."""

    codigo_lote = models.CharField(max_length=50, unique=True, db_index=True)
    material = models.ForeignKey(
        MaterialConstruccion, on_delete=models.CASCADE, related_name="lotes"
    )
    cantidad = models.PositiveIntegerField()
    fecha_entrada = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField(null=True, blank=True, db_index=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "lote_material"
        ordering = ["-fecha_entrada"]
        verbose_name = "Lote de Material"
        verbose_name_plural = "Lotes de Material"

    def __str__(self):
        return f"Lote {self.codigo_lote} - {self.material.nombre}"

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.now().date()).days

    def proximo_a_vencer(self):
        """True si vence en <=30 días."""
        d = self.dias_para_vencer
        return d is not None and 0 <= d <= 30
