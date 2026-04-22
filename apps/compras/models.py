from django.db import models
from apps.usuarios.models import Material
 
class Proveedor(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre del Proveedor")
    nit = models.CharField(max_length=20, unique=True, verbose_name="NIT/ID")
    contacto = models.CharField(max_length=100, verbose_name="Persona de Contacto")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    email = models.EmailField(verbose_name="Correo Electrónico")
    direccion = models.TextField(verbose_name="Dirección")
    estado = models.BooleanField(default=True, verbose_name="Activo")
 
    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
 
    def __str__(self):
        return self.nombre
 
 
class Compra(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, verbose_name="Proveedor")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Compra")
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name="Total Compra")
 
    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
 
    def calcular_total(self):
        """Recalcula el total sumando todos los subtotales de los detalles."""
        from decimal import Decimal
        self.total = sum(
            (d.cantidad * d.precio_unitario for d in self.detalles.all()),
            Decimal('0.00')
        )
        self.save(update_fields=['total'])
 
    def __str__(self):
        return f"Compra #{self.pk} — {self.proveedor}"
 
 
class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        related_name="detalles",
        verbose_name="Compra"
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        verbose_name="Material"
    )
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Precio de Compra"
    )
 
    class Meta:
        verbose_name = "Detalle de Compra"
        verbose_name_plural = "Detalles de Compra"
 
    def save(self, *args, **kwargs):
        es_nuevo = not self.pk
        super().save(*args, **kwargs)
        # CT-460 / CT-463: actualizar stock solo en creación
        if es_nuevo:
            self.material.stock += self.cantidad
            self.material.save(update_fields=['stock'])
 
    def __str__(self):
        return f"{self.material} x{self.cantidad}"
 
 
# ── HU-23 ──────────────────────────────────────────────────────────────────
from django.utils import timezone
 
 
def _generar_numero_orden():
    anio = timezone.now().year
    ultimo = OrdenCompra.objects.filter(numero_orden__startswith=f'OC-{anio}-').count()
    return f'OC-{anio}-{str(ultimo + 1).zfill(4)}'
 
 
class OrdenCompra(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('aprobada',  'Aprobada'),
        ('recibida',  'Recibida'),
        ('rechazada', 'Rechazada'),
    ]
    numero_orden   = models.CharField(max_length=20, unique=True, editable=False)
    proveedor      = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT,
        related_name='ordenes_compra',
        verbose_name='Proveedor'
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')
    observaciones  = models.TextField(blank=True, null=True, verbose_name='Observaciones')
    total          = models.DecimalField(max_digits=14, decimal_places=2, default=0, verbose_name='Total')
    estado         = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='pendiente', verbose_name='Estado'
    )
 
    class Meta:
        verbose_name        = 'Orden de Compra'
        verbose_name_plural = 'Órdenes de Compra'
        ordering            = ['-fecha_registro']
 
    def save(self, *args, **kwargs):
        if not self.pk:
            self.numero_orden = _generar_numero_orden()
        super().save(*args, **kwargs)
 
    def calcular_total(self):
        self.total = sum(d.subtotal for d in self.items.all())
        self.save(update_fields=['total'])
 
    def __str__(self):
        return f'{self.numero_orden} — {self.proveedor}'
 
 
class ItemOrdenCompra(models.Model):
    orden           = models.ForeignKey(
        OrdenCompra, on_delete=models.CASCADE,
        related_name='items'
    )
    nombre_material = models.CharField(max_length=200, verbose_name='Material')
    cantidad        = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Cantidad')
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Precio unitario')
    subtotal        = models.DecimalField(max_digits=14, decimal_places=2, editable=False, default=0)
 
    class Meta:
        verbose_name = 'Ítem de Orden'
 
    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)
 
    def __str__(self):
        return f'{self.nombre_material} x{self.cantidad}'
 




