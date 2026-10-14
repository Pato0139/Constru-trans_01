from django.conf import settings
from django.db import models
from django.utils.timezone import now


class Historial(models.Model):
    ACCIONES = [
        ("crear", "Crear"),
        ("editar", "Editar"),
        ("eliminar", "Eliminar"),
        ("login", "Inicio de sesión"),
        ("logout", "Cierre de sesión"),
        ("otro", "Otro"),
    ]

    # Campos del MER
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auditoria",
        verbose_name="Usuario",
    )
    accion = models.CharField(max_length=20, choices=ACCIONES, verbose_name="Acción")
    tabla = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tabla")
    registro_id = models.IntegerField(
        blank=True, null=True, verbose_name="ID del Registro"
    )
    fecha = models.DateTimeField(default=now, verbose_name="Fecha")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")

    # Campos legacy / compatibilidad (fuera del MER pero útiles)
    sincronizado = models.BooleanField(default=False)
    modulo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Módulo")
    elemento_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="ID Legacy")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción detallada")
    fecha_hora = models.DateTimeField(default=now, blank=True, null=True, verbose_name="Fecha y Hora")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Legacy")

    class Meta:
        verbose_name = "Historial de Actividad"
        verbose_name_plural = "Historial de Actividades"
        ordering = ["-fecha"]
        db_table = "historial"

    def __str__(self):
        return f"{self.usuario} - {self.accion} - {self.tabla or self.modulo} ({self.fecha})"

    def save(self, *args, **kwargs):
        if not self.modulo and self.tabla:
            self.modulo = self.tabla
        if not self.tabla and self.modulo:
            self.tabla = self.modulo
        if not self.elemento_id and self.registro_id is not None:
            self.elemento_id = str(self.registro_id)
        if self.registro_id is None and self.elemento_id and self.elemento_id.isdigit():
            self.registro_id = int(self.elemento_id)
        if not self.ip_address and self.ip:
            self.ip_address = self.ip
        if not self.ip and self.ip_address:
            self.ip = self.ip_address
        if self.fecha_hora is None and self.fecha:
            self.fecha_hora = self.fecha
        if self.fecha is None and self.fecha_hora:
            self.fecha = self.fecha_hora
        super().save(*args, **kwargs)
