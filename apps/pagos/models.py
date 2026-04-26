from django.db import models
from apps.facturacion.models import Factura

class Pago(models.Model):
    METODOS = [('efectivo', 'Efectivo'), ('transferencia', 'Transferencia'),
               ('tarjeta', 'Tarjeta'), ('nequi', 'Nequi')]
    
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='pagos')
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=METODOS)
    referencia = models.CharField(max_length=100, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'pago'

    def __str__(self):
        return f"Pago de {self.monto} a {self.factura.numero}"

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Pago)
def notificar_pago_admin(sender, instance, created, **kwargs):
    if created:
        from django.apps import apps
        Usuario = apps.get_model('usuarios', 'Usuario')
        Notificacion = apps.get_model('usuarios', 'Notificacion')
        
        # 1. Notificar a los administradores
        admins = Usuario.objects.filter(rol='admin')
        cliente_nombre = f"{instance.factura.cliente.nombres} {instance.factura.cliente.apellidos}"
        mensaje = f"Nuevo pago registrado de {cliente_nombre} por ${instance.monto} para la Factura {instance.factura.numero}"
        
        for admin in admins:
            Notificacion.objects.create(
                usuario=admin,
                mensaje=mensaje,
                link=f"/facturacion/"
            )
        
        # 2. Actualizar estado de la factura si está pagada por completo
        factura = instance.factura
        if factura.saldo_pendiente <= 0 and factura.estado != 'pagada':
            factura.estado = 'pagada'
            factura.save()
