from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.db.utils import OperationalError
import datetime
import logging

logger = logging.getLogger(__name__)

def validar_fecha_no_pasada(value):
    today = timezone.now().date()
    if isinstance(value, datetime.datetime):
        value = value.date()
    if value and value < today:
        raise ValidationError("La fecha no puede ser en el pasado.")



# =====================================================================
# PEDIDO
# =====================================================================
class Pedido(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("autorizado_despacho", "Autorizado para despacho"),
        ("vehiculo_asignado", "Vehículo asignado"),
        ("en_ruta", "En Ruta"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]
    PENDIENTE = "pendiente"
    AUTORIZADO_DESPACHO = "autorizado_despacho"
    VEHICULO_ASIGNADO = "vehiculo_asignado"
    EN_RUTA = "en_ruta"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"

    codigo_pedido = models.AutoField(primary_key=True)
    catalogo = models.ForeignKey(
        "usuarios.Catalogo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pedidos",
        db_column="pedido_codigo_catalogo",
    )
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
    fecha_entrega_programada = models.DateTimeField(null=True, blank=True, validators=[validar_fecha_no_pasada])
    fecha = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, blank=True)
    conductor = models.ForeignKey(
        "usuarios.Conductor",
        on_delete=models.SET_NULL,
        related_name="pedidos_asignados",
        null=True,
        blank=True,
    )
    conductor_usuario_legacy = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        related_name="pedidos_conductor_legacy",
        null=True,
        blank=True,
        limit_choices_to={"rol": "conductor"},
        db_column="conductor_usuario_id_legacy",
    )
    fecha_toma_entrega = models.DateTimeField(null=True, blank=True)
    fecha_entrega_real = models.DateTimeField(null=True, blank=True)
    sincronizado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha_solicitud"]
        db_table = "pedido"
        permissions = (
            ("aprobar_pedido", "Puede aprobar pedidos"),
            ("autorizar_despacho", "Puede autorizar despacho"),
            ("asignar_vehiculo", "Puede asignar vehículo a entrega"),
        )
        constraints = [
            models.CheckConstraint(
                check=models.Q(total__gte=0),
                name="chk_pedido_total_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(precio__gte=0) | models.Q(precio__isnull=True),
                name="chk_pedido_precio_gte_0",
            ),
        ]

    def __str__(self):
        return f"Pedido {self.codigo_pedido} - {self.estado}"

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

    @property
    def codigo_pedido_ref(self):
        return f"PED-{self.codigo_pedido:06d}"

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
        return self.conductor_usuario_legacy

    def save(self, *args, **kwargs):
        if self.conductor_id and not self.conductor_usuario_legacy_id:
            try:
                self.conductor_usuario_legacy = self.conductor.usuario
            except AttributeError as exc:
                logger.warning(
                    "No se pudo resolver usuario legacy del conductor en pedido %s: %s",
                    getattr(self, "codigo_pedido", "?"), exc,
                )
            except OperationalError as exc:
                logger.error(
                    "Error operativo resolviendo conductor_usuario_legacy en pedido %s: %s",
                    getattr(self, "codigo_pedido", "?"), exc,
                )
        super().save(*args, **kwargs)


# =====================================================================
# DETALLE_PEDIDO
# =====================================================================
class DetallePedido(models.Model):
    id_detalle_pedido = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    material = models.ForeignKey("usuarios.MaterialConstruccion", on_delete=models.PROTECT, db_column="cod_material")
    cantidad = models.IntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )

    class Meta:
        db_table = "detalle_pedido"
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name="chk_detalle_pedido_cantidad_gt_0",
            ),
            models.CheckConstraint(
                check=models.Q(precio_unitario__gte=0),
                name="chk_detalle_pedido_precio_unitario_gte_0",
            ),
            models.UniqueConstraint(
                fields=["pedido", "material"],
                name="uq_detalle_pedido_pedido_material",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.material.nombre}"

    def save(self, *args, **kwargs):
        using = kwargs.get("using", self._state.db)
        super().save(*args, **kwargs)
        self.pedido.calcular_total(using=using)

    @property
    def id(self):
        return self.id_detalle_pedido

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    @property
    def cliente(self):
        """Acceso por camino natural: Pedido -> Cliente (siguiendo MER)."""
        return self.pedido.cliente if self.pedido_id else None


# =====================================================================
# ENTREGA
# =====================================================================
class Entrega(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("en_ruta", "En Ruta"), ("entregado", "Entregado")]

    id_entrega = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="entregas")
    conductor = models.ForeignKey(
        "usuarios.Conductor", on_delete=models.PROTECT, related_name="entregas"
    )
    vehiculo = models.ForeignKey(
        "usuarios.Vehiculo", on_delete=models.SET_NULL, null=True, blank=True, related_name="entregas"
    )
    fecha_salida = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    direccion_entrega = models.CharField(max_length=200)

    # Campos legacy / compatibilidad
    conductor_usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={"rol": "conductor"},
        db_column="entrega_conductor_usuario_id",
    )
    sincronizado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha_salida"]
        db_table = "entrega"
        permissions = (
            ("registrar_entrega", "Puede registrar entregas"),
            ("confirmar_entrega", "Puede confirmar entregas"),
        )

    def __str__(self):
        ref = self.pedido.codigo_pedido_ref
        return f"Entrega {self.id_entrega} - Pedido {ref}"

    @property
    def id(self):
        return self.id_entrega

    def save(self, *args, **kwargs):
        if self.conductor_id and not self.conductor_usuario_id:
            try:
                self.conductor_usuario = self.conductor.usuario
            except AttributeError as exc:
                logger.warning(
                    "No se pudo resolver usuario de entrega en pedido %s: %s",
                    getattr(self.pedido, "codigo_pedido", "?"), exc,
                )
        super().save(*args, **kwargs)


Orden = Pedido
DetalleOrden = DetallePedido