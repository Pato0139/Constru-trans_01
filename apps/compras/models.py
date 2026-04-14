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

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.title()
        if self.contacto:
            self.contacto = self.contacto.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

class Compra(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, verbose_name="Proveedor")
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Compra")
    total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Total Compra")

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles")
    material = models.ForeignKey(Material, on_delete=models.CASCADE, verbose_name="Material")
    cantidad = models.PositiveIntegerField(verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Precio de Compra")

    def save(self, *args, **kwargs):
        # Actualizar stock automáticamente al guardar el detalle de compra (Requerimiento 20)
        if not self.pk: # Solo en creación
            self.material.stock_actual += self.cantidad
            self.material.save()
        super().save(*args, **kwargs)
