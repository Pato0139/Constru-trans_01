"""
Sesión de conteo físico de inventario (auditoría).
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from usuarios.models import MaterialConstruccion


class SesionConteo(models.Model):
    """Sesión de auditoría de inventario físico."""

    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("en_progreso", "En Progreso"),
        ("completado", "Completado"),
        ("cancelado", "Cancelado"),
    ]

    codigo = models.CharField(max_length=50, unique=True, db_index=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="conteos"
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "sesion_conteo"
        ordering = ["-fecha_inicio"]
        verbose_name = "Sesión de Conteo"
        verbose_name_plural = "Sesiones de Conteo"

    def __str__(self):
        return f"Conteo {self.codigo} - {self.get_estado_display()}"

    def iniciar(self):
        self.estado = "en_progreso"
        self.save(update_fields=["estado"])

    def completar(self):
        self.estado = "completado"
        self.fecha_fin = timezone.now()
        self.save(update_fields=["estado", "fecha_fin"])

    def cancelar(self, motivo=""):
        self.estado = "cancelado"
        self.fecha_fin = timezone.now()
        if motivo:
            self.observaciones += f"\n[CANCELADO] {motivo}"
        self.save(update_fields=["estado", "fecha_fin", "observaciones"])


class ConteoItem(models.Model):
    """Item individual de conteo en una sesión."""

    sesion = models.ForeignKey(SesionConteo, on_delete=models.CASCADE, related_name="items")
    material = models.ForeignKey(MaterialConstruccion, on_delete=models.CASCADE)
    cantidad_sistema = models.PositiveIntegerField()
    cantidad_fisica = models.PositiveIntegerField()
    diferencia = models.IntegerField(editable=False)
    observaciones = models.TextField(blank=True)
    fecha_conteo = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "conteo_item"
        unique_together = ("sesion", "material")
        verbose_name = "Item de Conteo"
        verbose_name_plural = "Items de Conteo"

    def __str__(self):
        return f"{self.material.nombre}: {self.cantidad_sistema} vs {self.cantidad_fisica}"

    def save(self, *args, **kwargs):
        self.diferencia = self.cantidad_fisica - self.cantidad_sistema
        super().save(*args, **kwargs)
