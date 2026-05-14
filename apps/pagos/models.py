
from django.db import models
from apps.facturacion.models import Factura
from apps.usuarios.models import MetodoPago


# =====================================================================
# PAGO  (MER: #id_pago *id_factura *monto *fecha *codigo_metodo_pago)
# =====================================================================
class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    codigo_metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT,
                                           db_column='codigo_metodo_pago')

    # Fuera del MER pero útil — NO se toca
    referencia = models.CharField(max_length=100, blank=True)
    registrado_por = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'pago'

    def __str__(self):
        return f"Pago {self.id_pago} - ${self.monto}"


# Signal: actualiza estado de factura
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Pago)
def actualizar_estado_factura(sender, instance, created, **kwargs):
    if created:
        factura = instance.factura
        if factura.saldo_pendiente <= 0 and factura.estado != 'pagada':
            factura.estado = 'pagada'
            factura.save()
