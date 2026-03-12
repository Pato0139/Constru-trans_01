from django.db import models
from Usuarios.models import Usuario


class Orden(models.Model):

    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="ordenes_cliente"
    )

    conductor = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_conductor"
    )

    direccion_origen = models.CharField(max_length=200)
    direccion_destino = models.CharField(max_length=200)

    fecha = models.DateTimeField(auto_now_add=True)

    estado = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("en_ruta", "En Ruta"),
            ("entregado", "Entregado"),
        ],
        default="pendiente"
    )

    def __str__(self):
        return f"Orden {self.id} - {self.estado}"
    
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)