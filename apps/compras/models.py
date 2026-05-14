
from django.db import models
from django.contrib.auth.models import User
from apps.usuarios.models import MaterialConstruccion, Proveedor


# =====================================================================
# COMPRA  (MER: #id_compra *codigo_proveedor *fecha_compra
#          *total_compra *estado *id_usuario)
# =====================================================================
class Compra(models.Model):
    ESTADOS = [('pendiente', 'Pendiente'), ('recibida', 'Recibida'), ('cancelada', 'Cancelada')]

    id_compra = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    # Fuera del MER pero útil — NO se toca
    observaciones = models.TextField(blank=True, null=True)
    sincronizado = models.BooleanField(default=False)

    @property
    def numero_orden(self):
        return f"OC-{self.fecha_compra.year}-{self.id_compra:04d}"

    def calcular_total(self):
        self.total_compra = sum(d.subtotal for d in self.detalles.all())
        self.save()
        return self.total_compra

    class Meta:
        ordering = ['-fecha_compra']
        db_table = 'compra'

    def __str__(self):
        return f"{self.numero_orden} - {self.proveedor.nombre_empresa}"


# =====================================================================
# DETALLE_COMPRA  (MER: #id_detalle_compra *id_compra *cod_material
#                  -cantidad -precio_unitario -subtotal)
# =====================================================================
class DetalleCompra(models.Model):
    id_detalle_compra = models.AutoField(primary_key=True)
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles')
    material = models.ForeignKey(MaterialConstruccion, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.compra.calcular_total()

    class Meta:
        db_table = 'detalle_compra'

    def __str__(self):
        return f"{self.cantidad} x {self.material.nombre}"
