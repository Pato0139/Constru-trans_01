from django.db import models, transaction
from apps.usuarios.models import Material, Proveedor

class Compra(models.Model):
    PENDIENTE = 'pendiente'
    RECIBIDA = 'recibida'
    CANCELADA = 'cancelada'
    
    ESTADOS = [
        (PENDIENTE, 'Pendiente'),
        (RECIBIDA, 'Recibida'),
        (CANCELADA, 'Cancelada'),
    ]

    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, verbose_name="Proveedor")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Compra")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Compra")
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE, verbose_name="Estado")
    observaciones = models.TextField(blank=True, null=True, verbose_name="Observaciones")
    sincronizado = models.BooleanField(default=False)

    @property
    def numero_orden(self):
        return f"OC-{self.fecha.year}-{self.id:04d}"

    def calcular_total(self):
        self.total = sum(d.subtotal for d in self.detalles.all())
        self.save()
        return self.total

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ['-fecha']
        db_table = 'compra'

    def __str__(self):
        return f"{self.numero_orden} - {self.proveedor.nombre}"

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles")
    material = models.ForeignKey(Material, on_delete=models.CASCADE, verbose_name="Material")
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio de Compra")

    class Meta:
        db_table = 'detalle_compra'

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def save(self, *args, **kwargs):
        # Solo actualizar stock y registrar movimiento si la compra pasa a 'recibida'
        # o si ya estaba recibida y se agrega un nuevo detalle (caso raro)
        # Por ahora, mantendremos la lógica original pero solo si el estado de la compra es 'recibida'
        # Pero según el HU-23, se guarda como 'pendiente'. El stock debería actualizarse al cambiar a 'recibida'.
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Recalcular el total de la compra
        self.compra.calcular_total()

    def __str__(self):
        return f"{self.cantidad} x {self.material.nombre} ({self.compra.numero_orden})"
