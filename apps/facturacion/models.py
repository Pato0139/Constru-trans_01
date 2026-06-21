from django.db import models


# =====================================================================
# FACTURA
# =====================================================================
class Factura(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("pagada", "Pagada"), ("anulada", "Anulada")]

    id_factura = models.AutoField(primary_key=True)
    pedido = models.OneToOneField(
        "ordenes.Pedido", on_delete=models.PROTECT, related_name="factura", null=True, blank=True
    )
    cliente = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.PROTECT, related_name="facturas", null=True, blank=True
    )
    numero = models.CharField(max_length=50, unique=True, null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, null=True, blank=True
    )
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default="pendiente")

    # NO se toca
    sincronizado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha"]
        db_table = "factura"

    def __str__(self):
        return (
            f"Factura {self.numero} - Pedido {self.pedido.codigo_pedido if self.pedido else 'N/A'}"
        )

    @property
    def total_pagado(self):
        return sum(p.monto for p in self.pagos.all())

    @property
    def saldo_pendiente(self):
        return self.total - self.total_pagado

    @property
    def orden(self):
        return self.pedido
