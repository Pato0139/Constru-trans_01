import datetime
import logging

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinValueValidator
from django.db import models
from django.db.utils import OperationalError
from django.utils import timezone

from apps.catalogo.models import MaterialConstruccion
from apps.pagos.models import Pago, comprobante_upload_to  # noqa: F401, E402
from apps.usuarios.models import Usuario
from config.state_machine import TransicionMixin
from config.validators import cantidad_validators, no_negativo, no_solo_espacios, porcentaje_validators

logger = logging.getLogger(__name__)


def validar_fecha_no_pasada(value):
    today = timezone.now().date()
    if isinstance(value, datetime.datetime):
        value = value.date()
    if value and value < today:
        raise ValidationError("La fecha no puede ser en el pasado.")


class Pedido(TransicionMixin, models.Model):
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

    # Fuente de verdad del flujo. "entregado" y "cancelado" son finales.
    TRANSICIONES = {
        PENDIENTE: {AUTORIZADO_DESPACHO, CANCELADO},
        AUTORIZADO_DESPACHO: {VEHICULO_ASIGNADO, EN_RUTA, CANCELADO, PENDIENTE},
        VEHICULO_ASIGNADO: {EN_RUTA, ENTREGADO, CANCELADO, PENDIENTE},
        EN_RUTA: {ENTREGADO, CANCELADO},
        ENTREGADO: set(),
        CANCELADO: set(),
    }
    ESTADOS_REQUIEREN_PAGO = {AUTORIZADO_DESPACHO, VEHICULO_ASIGNADO, EN_RUTA}

    codigo_pedido = models.AutoField(primary_key=True)
    catalogo = models.ForeignKey(
        "catalogo.Catalogo",
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
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
    impuesto_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, validators=porcentaje_validators
    )
    descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
    observacion_admin = models.TextField(blank=True, default="", validators=[MaxLengthValidator(2000)])
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    direccion_origen = models.CharField(max_length=200, default="Bodega Central", validators=[no_solo_espacios])
    direccion_destino = models.CharField(max_length=200, default="", validators=[no_solo_espacios])
    fecha_entrega_programada = models.DateTimeField(
        null=True, blank=True, validators=[validar_fecha_no_pasada]
    )
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
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0) & models.Q(impuesto__gte=0) & models.Q(descuento__gte=0),
                name="chk_pedido_montos_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(impuesto_porcentaje__gte=0) & models.Q(impuesto_porcentaje__lte=100),
                name="chk_pedido_impuesto_pct_0_100",
            ),
            models.CheckConstraint(
                check=models.Q(fecha_entrega_real__isnull=True)
                | models.Q(fecha_toma_entrega__isnull=True)
                | models.Q(fecha_entrega_real__gte=models.F("fecha_toma_entrega")),
                name="chk_pedido_entrega_real_gte_toma",
            ),
            models.CheckConstraint(
                check=models.Q(estado__in=[
                    "pendiente", "autorizado_despacho", "vehiculo_asignado",
                    "en_ruta", "entregado", "cancelado",
                ]),
                name="chk_pedido_estado_valido",
            ),
        ]

    def __str__(self):
        return f"Pedido {self.codigo_pedido} - {self.estado}"

    def clean(self):
        super().clean()
        errores = {}
        if (
            self.fecha_toma_entrega
            and self.fecha_entrega_real
            and self.fecha_entrega_real < self.fecha_toma_entrega
        ):
            errores["fecha_entrega_real"] = "La fecha de entrega no puede ser anterior a la toma de la entrega."
        if self.estado == self.ENTREGADO and not self.fecha_entrega_real:
            errores["fecha_entrega_real"] = "Un pedido entregado debe tener fecha de entrega real."
        if self.estado in (self.EN_RUTA, self.ENTREGADO) and not (
            self.direccion_destino or ""
        ).strip():
            errores["direccion_destino"] = "La dirección de destino es obligatoria para despachar."

        if self.impuesto_porcentaje is not None and not (0 <= self.impuesto_porcentaje <= 100):
            errores["impuesto_porcentaje"] = "El porcentaje de impuesto debe estar entre 0 y 100."
        if self.subtotal is not None and self.subtotal < 0:
            errores["subtotal"] = "El subtotal no puede ser negativo."
        if self.impuesto is not None and self.impuesto < 0:
            errores["impuesto"] = "El impuesto no puede ser negativo."
        if self.descuento is not None and self.descuento < 0:
            errores["descuento"] = "El descuento no puede ser negativo."
        if self.total is not None and self.total < 0:
            errores["total"] = "El total no puede ser negativo."

        if (
            self.subtotal is not None
            and self.impuesto is not None
            and self.descuento is not None
            and self.total is not None
        ):
            esperado = self.subtotal + self.impuesto - self.descuento
            if self.total != esperado:
                errores["total"] = f"El total ({self.total}) debe coincidir con subtotal + impuesto - descuento ({esperado})."

        if errores:
            raise ValidationError(errores)

    def calcular_total(self, using=None):
        if using is None:
            using = self._state.db
        self.subtotal = sum(d.subtotal for d in self.detalles.using(using).all())
        self.total = self.subtotal + (self.impuesto or 0) - (self.descuento or 0)
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
        if self.cliente_id and self.cliente:
            return self.cliente.usuario
        return self.usuario

    @property
    def conductor_usuario(self):
        if self.conductor:
            return self.conductor.usuario
        return self.conductor_usuario_legacy

    @property
    def pago_actual(self):
        from django.core.exceptions import ObjectDoesNotExist

        try:
            return self.pago
        except (ObjectDoesNotExist, AttributeError):
            return None

    @property
    def puede_despacharse(self):
        if self.estado in (self.AUTORIZADO_DESPACHO, self.VEHICULO_ASIGNADO):
            return True
        pago = self.pago_actual
        if not pago:
            return False
        if getattr(pago, "metodo", "") == Pago.METODO_CONTRAENTREGA:
            return pago.estado == Pago.APROBADO
        return bool(pago.habilita_despacho())

    def save(self, *args, **kwargs):
        if self.conductor_id and not self.conductor_usuario_legacy_id:
            try:
                self.conductor_usuario_legacy = self.conductor.usuario
            except AttributeError as exc:
                logger.warning(
                    "No se pudo resolver usuario legacy del conductor en pedido %s: %s",
                    getattr(self, "codigo_pedido", "?"),
                    exc,
                )
            except OperationalError as exc:
                logger.error(
                    "Error operativo resolviendo conductor_usuario_legacy en pedido %s: %s",
                    getattr(self, "codigo_pedido", "?"),
                    exc,
                )
        super().save(*args, **kwargs)


class DetallePedido(models.Model):
    id_detalle_pedido = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    material = models.ForeignKey(
        "catalogo.MaterialConstruccion", on_delete=models.PROTECT, db_column="cod_material"
    )
    cantidad = models.IntegerField(validators=cantidad_validators)
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

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
        if self.cantidad and self.precio_unitario:
            self.subtotal = self.cantidad * self.precio_unitario
        using = kwargs.get("using", self._state.db)
        super().save(*args, **kwargs)
        self.pedido.calcular_total(using=using)

    @property
    def id(self):
        return self.id_detalle_pedido

    @property
    def cliente(self):
        return self.pedido.cliente if self.pedido_id else None


Orden = Pedido
DetalleOrden = DetallePedido


class SolicitudPedido(TransicionMixin, models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("aprobado", "Aprobado"),
        ("cancelado", "Cancelado"),
        ("en_camino", "En camino"),
        ("entregado", "Entregado"),
    ]
    TRANSICIONES = {
        "pendiente": {"aprobado", "cancelado"},
        "aprobado": {"en_camino", "cancelado"},
        "en_camino": {"entregado", "cancelado"},
        "entregado": set(),
        "cancelado": set(),
    }

    cliente = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="pedidos_gestion",
        help_text="Cliente que crea el pedido.",
    )
    fecha_creacion = models.DateTimeField(default=timezone.now, editable=False)
    estado = models.CharField(
        max_length=12,
        choices=ESTADO_CHOICES,
        default="pendiente",
        help_text="Estado del ciclo de vida del pedido.",
    )
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Descuento global aplicado al total bruto.",
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        editable=False,
        help_text="Total neto después de aplicar descuento.",
    )

    class Meta:
        db_table = "gestion_pedido"
        verbose_name = "Solicitud de Pedido"
        verbose_name_plural = "Solicitudes de Pedido"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(descuento__gte=0) & models.Q(total__gte=0),
                name="chk_solicitud_descuento_total_gte_0",
            ),
        ]

    def __str__(self):
        return f"Solicitud #{self.id} – {self.cliente}"

    def calcular_total(self):
        bruto = sum(det.subtotal for det in self.detalles.all())
        self.total = max(bruto - self.descuento, 0)
        self.save(update_fields=["total"])
        return self.total


class DetalleSolicitudPedido(models.Model):
    pedido = models.ForeignKey(SolicitudPedido, on_delete=models.CASCADE, related_name="detalles")
    material = models.ForeignKey(
        MaterialConstruccion,
        on_delete=models.PROTECT,
        related_name="detalles_pedidos_gestion",
        help_text="Material solicitado.",
    )
    cantidad = models.PositiveIntegerField(
        validators=cantidad_validators, help_text="Cantidad solicitada."
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Precio unitario al momento del pedido.",
    )

    class Meta:
        db_table = "gestion_detalle_pedido"
        verbose_name = "Detalle de Solicitud de Pedido"
        verbose_name_plural = "Detalles de Solicitud de Pedido"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f"{self.cantidad} × {self.material.nombre}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.precio_unitario = self.material.precio

        super().save(*args, **kwargs)
        self.pedido.calcular_total()
# Re-export obligatorio: 0001_initial referencia apps.pedidos.models.comprobante_upload_to
from apps.pagos.models import Pago, comprobante_upload_to  # noqa: F401, E402
