from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator

class Orden(models.Model):
    cliente = models.ForeignKey(
        'clientes.Cliente', 
        on_delete=models.CASCADE, 
        related_name="ordenes"
    )
    conductor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ordenes_conductor"
    )

    direccion_origen = models.CharField(max_length=200, default="Bodega Central")
    direccion_destino = models.CharField(max_length=200, default="")
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_entrega_programada = models.DateTimeField(null=True, blank=True)
    fecha_toma_entrega = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)

    PENDIENTE = "pendiente"
    EN_RUTA = "en_ruta"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"

    ESTADOS = [
        (PENDIENTE, "Pendiente"),
        (EN_RUTA, "En Ruta"),
        (ENTREGADO, "Entregado"),
        (CANCELADO, "Cancelado"),
    ]

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=PENDIENTE
    )

    precio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    sincronizado = models.BooleanField(default=False)

    def calcular_total(self):
        """Recalcula el total basado en los detalles"""
        total = sum(d.cantidad * d.precio_unitario for d in self.detalles.all())
        self.precio = total
        self.save()
        return total

    class Meta:
        ordering = ["-fecha"]
        db_table = 'orden'

    def __str__(self):
        return f"Orden {self.id} - {self.estado}"


class DetalleOrden(models.Model):
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name="detalles"
    )
    material = models.ForeignKey(
        'usuarios.Material',
        on_delete=models.CASCADE
    )
    cantidad = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        db_table = 'detalle_orden'

    def __str__(self):
        return f"{self.cantidad} x {self.material.nombre} (Orden {self.orden.id})"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


class Entrega(models.Model):
    pedido = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name="entregas"
    )
    conductor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE
    )
    vehiculo = models.ForeignKey(
        'usuarios.Vehiculo',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha = models.DateTimeField(auto_now_add=True)

    fecha_finalizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha"]
        db_table = 'entrega'

    estado = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("en_ruta", "En Ruta"),
            ("entregado", "Entregado"),
        ],
        default="pendiente"
    )
    sincronizado = models.BooleanField(default=False)

    def __str__(self):
        return f"Entrega {self.id} - Orden {self.pedido.id}"


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

@receiver(post_save, sender=Orden)
def post_save_orden(sender, instance, created, **kwargs):
    """Acciones automáticas al guardar una Orden"""
    from django.apps import apps
    from django.db.models import F
    from django.db import transaction

    # 1. Generar factura automáticamente cuando el pedido se marca como entregado
    if instance.estado == 'entregado' and not hasattr(instance, 'factura'):
        from apps.facturacion.models import Factura
        
        # Asegurar que el precio esté actualizado antes de facturar
        # Si el precio es 0, intentamos calcularlo de nuevo
        precio_final = instance.precio
        if precio_final <= 0:
            detalles = instance.detalles.all()
            if detalles.exists():
                precio_final = sum(d.cantidad * d.precio_unitario for d in detalles)
                # Actualizar el precio en la instancia para que coincida
                Orden.objects.filter(id=instance.id).update(precio=precio_final)

        Factura.objects.create(
            numero=f"F-{instance.id:06d}",
            orden=instance,
            cliente=instance.cliente.usuario,
            subtotal=precio_final,
            iva=0,
            total=precio_final
        )
        
        # 2. Descontar stock y registrar movimientos (Solo si no se ha hecho antes)
        Stock = apps.get_model('usuarios', 'Stock')
        MovimientoInventario = apps.get_model('inventario', 'MovimientoInventario')
        
        if not MovimientoInventario.objects.filter(referencia_id=instance.id, tipo='salida', motivo__icontains="orden").exists():
            with transaction.atomic():
                for detalle in instance.detalles.all():
                    stock_obj, _ = Stock.objects.get_or_create(
                        material=detalle.material,
                        defaults={'cantidad': 0}
                    )
                    stock_obj.cantidad = F('cantidad') - detalle.cantidad
                    stock_obj.save()
                    
                    MovimientoInventario.objects.create(
                        material=detalle.material,
                        tipo='salida',
                        cantidad=detalle.cantidad,
                        motivo=f"orden #{instance.id}",
                        referencia_id=instance.id,
                        usuario=None 
                    )

                # 3. Notificar a los administradores
                Notificacion = apps.get_model('usuarios', 'Notificacion')
                Usuario = apps.get_model('usuarios', 'Usuario')
                admins = Usuario.objects.filter(rol='admin')
                materiales_list = [f"{d.cantidad} x {d.material.nombre}" for d in instance.detalles.all()]
                activos_msg = ", ".join(materiales_list)
                
                # Obtener quién entregó si existe
                entrega = instance.entregas.filter(estado='entregado').first()
                conductor_msg = f" por {entrega.conductor.nombres}" if entrega else " (Marcar manual en admin)"
                
                mensaje = f"Pedido #{instance.id} entregado{conductor_msg}. Materiales: {activos_msg}"
                
                for admin in admins:
                    Notificacion.objects.create(
                        usuario=admin,
                        mensaje=mensaje,
                        link=f"/ordenes/pedido/{instance.id}/"
                    )

@receiver(post_save, sender=Entrega)
def actualizar_estado_orden(sender, instance, created, **kwargs):
    """Actualiza el estado de la orden solo cuando la entrega cambia a 'entregado'"""
    if instance.estado == 'entregado':
        pedido = instance.pedido
        if pedido.estado != Orden.ENTREGADO:
            pedido.estado = Orden.ENTREGADO
            pedido.fecha_entrega_real = timezone.now()
            pedido.save() # Esto disparará post_save_orden
            
    elif instance.estado == 'en_ruta':
        pedido = instance.pedido
        if pedido.estado != Orden.EN_RUTA:
            pedido.estado = Orden.EN_RUTA
            pedido.save()
