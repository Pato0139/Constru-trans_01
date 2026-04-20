from django.db import models
from apps.usuarios.models import Usuario, Vehiculo, Material
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator


class Orden(models.Model):
    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="ordenes_cliente"
    )
    conductor = models.ForeignKey(
        Usuario,
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

    def calcular_total(self):
        """Recalcula el total basado en los detalles"""
        total = sum(d.cantidad * d.precio_unitario for d in self.detalles.all())
        self.precio = total
        self.save()
        return total

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Orden {self.id} - {self.estado}"


class DetalleOrden(models.Model):
    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name="detalles"
    )
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE
    )
    cantidad = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

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
        Usuario,
        on_delete=models.CASCADE
    )
    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    estado = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("en_ruta", "En Ruta"),
            ("entregado", "Entregado"),
        ],
        default="pendiente"
    )

    def __str__(self):
        return f"Entrega de pedido {self.pedido.id}"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Orden)
def crear_factura_auto(sender, instance, **kwargs):
    """Genera la factura automáticamente cuando el pedido se marca como entregado"""
    if instance.estado == 'entregado' and not hasattr(instance, 'factura'):
        from apps.facturacion.models import Factura
        Factura.objects.create(
            numero=f"F-{instance.id:06d}",
            orden=instance,
            cliente=instance.cliente,
            subtotal=instance.precio,
            total=instance.precio
        )

@receiver(post_save, sender=Entrega)
def actualizar_estado_orden(sender, instance, created, **kwargs):
    """Actualiza el estado de la orden solo cuando la entrega cambia a 'entregado'"""
    if instance.estado == 'entregado':
        pedido = instance.pedido
        pedido.estado = Orden.ENTREGADO
        import datetime
        pedido.fecha_entrega_real = datetime.datetime.now()
        pedido.save()
    elif instance.estado == 'en_ruta':
        pedido = instance.pedido
        pedido.estado = Orden.EN_RUTA
        pedido.save()
