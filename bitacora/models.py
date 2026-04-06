from django.db import models
from django.contrib.auth.models import User

class Bitacora(models.Model):
    ACCIONES = [
        ('crear', 'Crear'),
        ('editar', 'Editar'),
        ('eliminar', 'Eliminar'),
        ('login', 'Inicio de sesión'),
        ('logout', 'Cierre de sesión'),
        ('otro', 'Otro'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuario")
    accion = models.CharField(max_length=20, choices=ACCIONES, verbose_name="Acción")
    modulo = models.CharField(max_length=50, verbose_name="Módulo/Elemento")
    elemento_id = models.CharField(max_length=50, null=True, blank=True, verbose_name="ID del Elemento")
    descripcion = models.TextField(verbose_name="Descripción detallada")
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")

    class Meta:
        verbose_name = "Registro de Bitácora"
        verbose_name_plural = "Registros de Bitácora"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"{self.usuario} - {self.accion} - {self.modulo} ({self.fecha_hora})"
