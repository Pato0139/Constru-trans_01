from django.db import models
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
    
    METODO_EFECTIVO = "efectivo"
    METODO_TRANSFERENCIA = "transferencia"
    METODO_TARJETA = "tarjeta"
    
    METODOS_PAGO = [
        (METODO_EFECTIVO, "Efectivo"),
        (METODO_TRANSFERENCIA, "Transferencia"),
        (METODO_TARJETA, "Tarjeta"),
    ]
    
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODOS_PAGO,
        default=METODO_EFECTIVO
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
