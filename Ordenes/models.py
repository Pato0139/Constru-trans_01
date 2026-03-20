from django.db import models
from usuarios.models import Usuario, Vehiculo, Material


# =========================
# ORDEN
# =========================
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

    direccion_origen = models.CharField(max_length=200)
    direccion_destino = models.CharField(max_length=200)

    fecha = models.DateTimeField(auto_now_add=True)

    estado = models.CharField(
        max_length=20,
        choices=[
            ("pendiente", "Pendiente"),
            ("en_ruta", "En Ruta"),
            ("entregado", "Entregado"),
        ],
        default="pendiente"
    )

    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # 🔥 Calcula el total de la orden basado en los detalles
    def calcular_total(self):
        total = sum(detalle.subtotal for detalle in self.detalles.all())
        self.precio = total
        self.save()

    def __str__(self):
        return f"Orden {self.id} - {self.estado}"


# =========================
# DETALLE DEL PEDIDO
# =========================
class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name="detalles"  # 🔴 CLAVE para tu HTML
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE
    )

    cantidad = models.PositiveIntegerField()

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    # 🔥 Calcula automáticamente el subtotal
    def save(self, *args, **kwargs):
        self.subtotal = self.material.precio * self.cantidad
        super().save(*args, **kwargs)

        # 🔥 Actualiza el total del pedido
        self.pedido.calcular_total()

    def __str__(self):
        return f"{self.material.nombre} x {self.cantidad}"


# =========================
# ENTREGA
# =========================
class Entrega(models.Model):
    pedido = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE
    )

    conductor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE
    )

    vehiculo = models.ForeignKey(
        Vehiculo,
        on_delete=models.CASCADE
    )

    fecha = models.DateTimeField()

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