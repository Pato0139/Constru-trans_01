
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.facturacion.models import Factura
from apps.ordenes.models import Pedido


# =====================================================================
# PAGO
# =====================================================================
class Pago(models.Model):
    ESTADOS_PAGO = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('fallido', 'Fallido'),
        ('reembolsado', 'Reembolsado'),
    ]

    id_pago = models.AutoField(primary_key=True)
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    codigo_metodo_pago = models.ForeignKey('usuarios.MetodoPago', db_column='codigo_metodo_pago', on_delete=models.PROTECT)
    estado = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='pendiente')
    
    # NO se toca
    referencia = models.CharField(max_length=255, blank=True, help_text="Número de referencia, comprobante, etc.")
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    sincronizado = models.BooleanField(default=False)
    
    # Campos adicionales para pagos online/transferencia
    comprobante = models.FileField(upload_to='comprobantes_pago/', blank=True, null=True, help_text="Sube el comprobante de pago (imagen o PDF)")
    notas = models.TextField(blank=True, help_text="Notas adicionales sobre el pago")

    class Meta:
        db_table = 'pago'

    def __str__(self):
        return f"Pago {self.id_pago} - ${self.monto} ({self.estado})"
    
    @property
    def es_completado(self):
        return self.estado == 'completado'


@receiver(post_save, sender=Pago)
def actualizar_estado_factura(sender, instance, created, **kwargs):
    if instance.estado == 'completado':
        factura = instance.factura
        # Recalcular el total pagado
        total_pagado = sum(pago.monto for pago in factura.pagos.filter(estado='completado'))
        if total_pagado >= factura.total and factura.estado != 'pagada':
            factura.estado = 'pagada'
            factura.save()
            # If factura has a pedido, keep it as 'pendiente' so admin can assign delivery
            if factura.pedido:
                pedido = factura.pedido
                # Just leave it as pendiente, or set to en_ruta if you want
                # pedido.estado = 'en_ruta'
                pedido.save()
