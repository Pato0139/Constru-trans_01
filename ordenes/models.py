from django.db import models
from usuarios.models import Usuario, Vehiculo, Material
from django.db.models.signals import post_save
from django.dispatch import receiver


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
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    cantidad = models.IntegerField(default=1)

    direccion_origen = models.CharField(max_length=200)
    direccion_destino = models.CharField(max_length=200)
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_entrega_programada = models.DateTimeField(null=True, blank=True)
    fecha_toma_entrega = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)

    PENDIENTE = "pendiente"
    EN_RUTA = "en_ruta"
    ENTREGADO = "entregado"

    ESTADOS = [
        (PENDIENTE, "Pendiente"),
        (EN_RUTA, "En Ruta"),
        (ENTREGADO, "Entregado"),
    ]

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=PENDIENTE
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Orden {self.id} - {self.estado}"


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


@receiver(post_save, sender=Entrega)
def actualizar_estado_orden(sender, instance, created, **kwargs):
    if created:
        pedido = instance.pedido
        pedido.estado = Orden.ENTREGADO
        pedido.save()