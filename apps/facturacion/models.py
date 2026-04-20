from django.db import models
from apps.ordenes.models import Orden
from apps.usuarios.models import Usuario

class Factura(models.Model):
    PENDIENTE = 'pendiente'
    PAGADA = 'pagada'
    ANULADA = 'anulada'
    ESTADOS = [(PENDIENTE, 'Pendiente'), (PAGADA, 'Pagada'), (ANULADA, 'Anulada')]
    
    numero = models.CharField(max_length=20, unique=True)            # ej: F-000001
    orden = models.OneToOneField(Orden, on_delete=models.PROTECT, related_name='factura')
    cliente = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=15, choices=ESTADOS, default=PENDIENTE)
    
    class Meta:
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"Factura {self.numero} - {self.cliente}"

class Pago(models.Model):
    METODOS = [('efectivo', 'Efectivo'), ('transferencia', 'Transferencia'),
               ('tarjeta', 'Tarjeta'), ('nequi', 'Nequi')]
    
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=METODOS)
    referencia = models.CharField(max_length=100, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Pago de {self.monto} a {self.factura.numero}"
