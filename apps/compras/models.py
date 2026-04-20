from django.db import models, transaction
from apps.usuarios.models import Material, Proveedor

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
        # Actualizar stock automáticamente al guardar el detalle de compra
        if not self.pk: # Solo en creación
            from apps.usuarios.models import Stock
            from django.db.models import F
            with transaction.atomic():
                stock_obj, created = Stock.objects.select_for_update().get_or_create(material=self.material)
                stock_obj.cantidad = F('cantidad') + self.cantidad
                stock_obj.save()
                
                # HU-17: Registrar movimiento
                from apps.inventario.models import MovimientoInventario
                MovimientoInventario.objects.create(
                    material=self.material,
                    tipo='entrada',
                    cantidad=self.cantidad,
                    motivo=f"compra #{self.compra.id}",
                    referencia_id=self.compra.id
                )
        super().save(*args, **kwargs)
