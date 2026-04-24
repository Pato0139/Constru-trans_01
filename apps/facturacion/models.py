from django.db import models

class Factura(models.Model):
    PENDIENTE = 'pendiente'
    PAGADA = 'pagada'
    ANULADA = 'anulada'
    ESTADOS = [(PENDIENTE, 'Pendiente'), (PAGADA, 'Pagada'), (ANULADA, 'Anulada')]
    
    numero = models.CharField(max_length=20, unique=True)            # ej: F-000001
    orden = models.OneToOneField('ordenes.Orden', on_delete=models.PROTECT, related_name='factura')
    cliente = models.ForeignKey('usuarios.Usuario', on_delete=models.PROTECT)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=15, choices=ESTADOS, default=PENDIENTE)
    
    class Meta:
        ordering = ['-fecha_emision']

    @property
    def total_pagado(self):
        return sum(pago.monto for pago in self.pagos.all())

    @property
    def saldo_pendiente(self):
        return self.total - self.total_pagado

    def __str__(self):
        return f"Factura {self.numero} - {self.cliente}"
