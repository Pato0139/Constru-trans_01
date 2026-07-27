from django.core.validators import MinValueValidator
from django.db import models


# =====================================================================
# PEDIDO
# =====================================================================
class Pedido(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("en_ruta", "En Ruta"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]
    PENDIENTE = "pendiente"
    EN_RUTA = "en_ruta"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"

    codigo_pedido = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        "usuarios.Usuario", on_delete=models.CASCADE, related_name="pedidos"
    )
    cliente = models.ForeignKey(
        "clientes.Cliente", on_delete=models.CASCADE, related_name="pedidos", null=True, blank=True
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    # NO se toca
    direccion_origen = models.CharField(max_length=200, default="Bodega Central")
    direccion_destino = models.CharField(max_length=200, default="")
    fecha_entrega_programada = models.DateTimeField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    conductor = models.ForeignKey(
        "usuarios.Conductor",
        on_delete=models.SET_NULL,
        related_name="pedidos_asignados",
        null=True,
        blank=True,
    )
    fecha_toma_entrega = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)
    sincronizado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha_solicitud"]
        db_table = "pedido"
        constraints = [
            models.CheckConstraint(
                check=models.Q(total__gte=0),
                name="chk_pedido_total_gte_0"
            ),
            models.CheckConstraint(
                check=models.Q(precio__gte=0),
                name="chk_pedido_precio_gte_0"
            ),
        ]

    def __str__(self):
        return f"Pedido {self.codigo_pedido} - {self.estado}"

    @property
    def cliente_usuario(self):
        """Usuario que realizó el pedido (perfil cliente o usuario directo)."""
        if self.cliente_id and self.cliente:
            return self.cliente.usuario
        return self.usuario

    @property
    def conductor_usuario(self):
        """Obtener el Usuario del Conductor asignado."""
        if self.conductor:
            return self.conductor.usuario
        return None

    def calcular_total(self, using=None):
        if using is None:
            using = self._state.db
        self.total = sum(d.subtotal for d in self.detalles.using(using).all())
        self.precio = self.total
        self.save(using=using)
        return self.total

    @property
    def id(self):
        return self.codigo_pedido


# =====================================================================
# DETALLE_PEDIDO
# =====================================================================
class DetallePedido(models.Model):
    id_detalle_pedido = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    material = models.ForeignKey("usuarios.MaterialConstruccion", on_delete=models.PROTECT)
    cantidad = models.IntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        db_table = "detalle_pedido"
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name="chk_detalle_pedido_cantidad_gt_0"
            ),
            models.CheckConstraint(
                check=models.Q(precio_unitario__gte=0),
                name="chk_detalle_pedido_precio_unitario_gte_0"
            ),
            models.UniqueConstraint(
                fields=["pedido", "material"],
                name="uq_detalle_pedido_pedido_material"
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.material.nombre}"

    def save(self, *args, **kwargs):
        using = kwargs.get("using", self._state.db)
        super().save(*args, **kwargs)
        self.pedido.calcular_total(using=using)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario


# =====================================================================
# ENTREGA
# =====================================================================
class Entrega(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("en_ruta", "En Ruta"), ("entregado", "Entregado")]

    id_entrega = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="entregas")
    conductor = models.ForeignKey(
        "usuarios.Conductor", on_delete=models.PROTECT, related_name="entregas_asignadas"
    )
    vehiculo = models.ForeignKey(
        "usuarios.Vehiculo", on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha_salida = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    direccion_entrega = models.CharField(max_length=200)

    # NO se toca
    sincronizado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha_salida"]
        db_table = "entrega"

    def __str__(self):
        return f"Entrega {self.id_entrega} - Pedido {self.pedido.codigo_pedido}"


# Alias para compatibilidad
Orden = Pedido
DetalleOrden = DetallePedido
