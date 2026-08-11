from django.db import models


# =====================================================================
# FACTURA
# =====================================================================
class Factura(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("pagada", "Pagada"), ("anulada", "Anulada")]

    id_factura = models.AutoField(primary_key=True)
    pedido = models.OneToOneField(
        "ordenes.Pedido", on_delete=models.PROTECT, related_name="factura"
    )
    numero = models.CharField(max_length=50, unique=True, blank=True, null=True)
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
        constraints = [
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0),
                name="chk_factura_subtotal_gte_0"
            ),
            models.CheckConstraint(
                check=models.Q(iva__gte=0),
                name="chk_factura_iva_gte_0"
            ),
            models.CheckConstraint(
                check=models.Q(total__gte=0),
                name="chk_factura_total_gte_0"
            ),
        ]

    def __str__(self):
        return (
            f"Factura {self.numero} - Pedido {self.pedido.codigo_pedido if self.pedido else 'N/A'}"
        )

    @property
    def cliente(self):
        """Obtener cliente desde el pedido (elimina redundancia)."""
        if self.pedido and self.pedido.cliente:
            return self.pedido.cliente.usuario
        elif self.pedido:
            return self.pedido.usuario
        return None

    @property
    def cliente_id(self):
        """Para compatibilidad con código antiguo."""
        cliente = self.cliente
        return cliente.id if cliente else None

    @property
    def total_pagado(self):
        return sum(p.monto for p in self.pagos.all())

    @property
    def saldo_pendiente(self):
        return self.total - self.total_pagado

    @property
    def orden(self):
        return self.pedido
