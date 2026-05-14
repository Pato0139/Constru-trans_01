
from django.db import models


# =====================================================================
# FACTURA  (MER: #id_factura(PK) #id_pedido(FK)(PK) *fecha *total *estado)
# =====================================================================
class Factura(models.Model):
    ESTADOS = [('pendiente', 'Pendiente'), ('pagada', 'Pagada'), ('anulada', 'Anulada')]

    id_factura = models.AutoField(primary_key=True)
    pedido = models.OneToOneField('ordenes.Pedido', on_delete=models.PROTECT,
                                   related_name='factura')
    fecha = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='pendiente')

    # Fuera del MER pero útil — NO se toca
    sincronizado = models.BooleanField(default=False)

    @property
    def total_pagado(self):
        return sum(p.monto for p in self.pagos.all())

    @property
    def saldo_pendiente(self):
        return self.total - self.total_pagado

    class Meta:
        ordering = ['-fecha']
        db_table = 'factura'

    def __str__(self):
        return f"Factura {self.id_factura} - Pedido {self.pedido.codigo_pedido}"
