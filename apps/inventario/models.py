from django.db import models
from apps.usuarios.models import Material
from django.contrib.auth.models import User

class MovimientoInventario(models.Model):
    ENTRADA = 'entrada'
    SALIDA = 'salida'
    TIPOS = [(ENTRADA, 'Entrada'), (SALIDA, 'Salida')]
    
    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.PositiveIntegerField()
    motivo = models.CharField(max_length=200, blank=True)  # "compra", "orden #12", "ajuste"
    referencia_id = models.PositiveIntegerField(null=True, blank=True)
    usuario = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tipo.upper()}: {self.cantidad} de {self.material.nombre}"
