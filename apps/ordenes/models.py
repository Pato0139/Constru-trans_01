from django.db import models
from apps.usuarios.models import Usuario, Vehiculo, Material
from django.db.models.signals import post_save, post_delete
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
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    cantidad = models.IntegerField(default=1, validators=[MinValueValidator(1)])

    direccion_origen = models.CharField(max_length=200)
    direccion_destino = models.CharField(max_length=200)
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
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Orden {self.id} - {self.estado}"

    # CT-272 CT-323 — Lógica de suma total
    def calcular_total(self):
        """Calcula el total sumando subtotales de todos los detalles."""
        total = sum(
            detalle.subtotal() for detalle in self.detalles.all()
        )
        # CT-276 — El total no puede ser negativo
        return max(total, 0)

    # CT-324 CT-325 CT-326 CT-327 — Actualiza y guarda el total
    def actualizar_total(self):
        """Recalcula y guarda el total en la base de datos."""
        self.precio = self.calcular_total()
        self.save(update_fields=['precio'])


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

    # CT-273 — Multiplicar cantidad x precio
    def subtotal(self):
        """Calcula el subtotal de este detalle: cantidad × precio_unitario."""
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


@receiver(post_save, sender=Entrega)
def actualizar_estado_orden(sender, instance, created, **kwargs):
    if created:
        pedido = instance.pedido
        pedido.estado = Orden.ENTREGADO
        pedido.save()


# CT-324 — Actualizar total al agregar detalle
@receiver(post_save, sender=DetalleOrden)
def actualizar_total_al_guardar(sender, instance, **kwargs):
    instance.orden.actualizar_total()


# CT-325 — Actualizar total al eliminar detalle
@receiver(post_delete, sender=DetalleOrden)
def actualizar_total_al_eliminar(sender, instance, **kwargs):
    instance.orden.actualizar_total()