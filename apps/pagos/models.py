import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from config.state_machine import TransicionMixin
from config.validators import ArchivoValidator, monto_positivo, no_negativo, no_solo_espacios

OBSERVACIONES_MAX = 1000


def comprobante_upload_to(instance, filename):
    pedido_id = getattr(instance, "pedido_id", None) or "sin_pedido"
    return f"comprobantes/pedido_{pedido_id}/{filename}"


def _evidencia_upload_to(instance, filename):
    factura_id = getattr(instance, "factura_id", None) or "sin_factura"
    ts = timezone.now().strftime("%Y/%m")
    return f"comprobantes/factura_{factura_id}/{ts}/{filename}"


class Pago(TransicionMixin, models.Model):
    METODO_NEQUI = "nequi"
    METODO_DAVIPLATA = "daviplata"
    METODO_BANCOLOMBIA = "bancolombia"
    METODO_CONTRAENTREGA = "contraentrega"
    METODOS = [
        (METODO_NEQUI, "Nequi"),
        (METODO_DAVIPLATA, "DaviPlata"),
        (METODO_BANCOLOMBIA, "Bancolombia"),
        (METODO_CONTRAENTREGA, "Contraentrega"),
    ]
    METODOS_CON_COMPROBANTE = {
        METODO_NEQUI,
        METODO_DAVIPLATA,
        METODO_BANCOLOMBIA,
    }

    PENDIENTE = "pendiente"
    APROBADO = "aprobado"
    RECHAZADO = "rechazado"
    ESTADOS = [
        (PENDIENTE, "Pendiente"),
        (APROBADO, "Aprobado"),
        (RECHAZADO, "Rechazado"),
    ]
    TRANSICIONES = {
        PENDIENTE: {APROBADO, RECHAZADO},
        RECHAZADO: {PENDIENTE},  # el cliente reenvía comprobante
        APROBADO: set(),
    }

    pedido = models.OneToOneField(
        "pedidos.Pedido",
        on_delete=models.CASCADE,
        related_name="pago",
        db_column="pedido_id",
    )
    metodo = models.CharField(max_length=20, choices=METODOS, db_column="codigo_metodo_pago")
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    comprobante = models.FileField(
        upload_to=comprobante_upload_to,
        null=True,
        blank=True,
        db_column="comprobante",
        validators=[ArchivoValidator(("png", "jpg", "jpeg"), max_mb=5)],
    )
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default=PENDIENTE, db_column="estado_pago"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")
    fecha_revision = models.DateTimeField(null=True, blank=True, db_column="fecha_actualizacion")
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos_revisados",
        db_column="revisado_por_id",
    )
    observaciones = models.TextField(
        blank=True, db_column="motivo_rechazo", validators=[MaxLengthValidator(OBSERVACIONES_MAX)]
    )

    class Meta:
        db_table = "pago_pedido"
        ordering = ["-fecha_registro"]
        permissions = (
            ("revisar_pago", "Puede revisar y aprobar o rechazar pagos"),
            ("registrar_pago", "Puede registrar un pago"),
        )
        constraints = [
            models.CheckConstraint(
                check=models.Q(monto__gte=0),
                name="chk_pago_monto_gte_0",
            ),
        ]

    def __str__(self):
        return f"Pago pedido {self.pedido_id} ({self.get_estado_display()})"

    def requiere_comprobante(self):
        return self.metodo in self.METODOS_CON_COMPROBANTE

    def habilita_despacho(self):
        return self.estado == self.APROBADO

    def clean(self):
        errores = {}
        if self.requiere_comprobante() and not self.comprobante:
            errores["comprobante"] = "Este método de pago requiere comprobante."
        if self.estado == self.RECHAZADO and not (self.observaciones or "").strip():
            errores["observaciones"] = "Indica el motivo del rechazo."
        if errores:
            raise ValidationError(errores)

    def marcar_revision(self, *, estado, revisor, observaciones=""):
        if estado not in (self.APROBADO, self.RECHAZADO):
            raise ValueError("La revisión solo admite aprobado o rechazado.")
        self.transicionar(estado)
        self.revisado_por = revisor
        self.observaciones = observaciones or ""
        self.fecha_revision = timezone.now()


class DetallePago(models.Model):
    pago = models.ForeignKey(
        Pago,
        on_delete=models.CASCADE,
        related_name="detalles",
        db_column="pago_id",
    )
    concepto = models.CharField(max_length=200, db_column="concepto", validators=[no_solo_espacios])
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        db_column="monto",
    )

    class Meta:
        db_table = "detalle_pago"
        constraints = [
            models.CheckConstraint(check=models.Q(monto__gte=0), name="chk_detalle_pago_monto_gte_0"),
        ]

    def __str__(self):
        return f"Detalle {self.concepto} - ${self.monto}"


class Factura(TransicionMixin, models.Model):
    class Estado(models.TextChoices):
        EMITIDA = "emitida", "Emitida"
        PARCIAL = "parcial", "Pago parcial"
        PAGADA = "pagada", "Pagada"
        VENCIDA = "vencida", "Vencida"
        ANULADA = "anulada", "Anulada"

    TRANSICIONES = {
        Estado.EMITIDA: {Estado.PARCIAL, Estado.PAGADA, Estado.VENCIDA, Estado.ANULADA},
        Estado.PARCIAL: {Estado.EMITIDA, Estado.PAGADA, Estado.VENCIDA, Estado.ANULADA},
        Estado.VENCIDA: {Estado.PARCIAL, Estado.PAGADA, Estado.ANULADA},
        Estado.PAGADA: set(),
        Estado.ANULADA: set(),
    }

    numero = models.CharField(max_length=20, unique=True, editable=False)
    pedido = models.OneToOneField(
        "pedidos.Pedido",
        on_delete=models.PROTECT,
        related_name="factura",
    )
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        related_name="facturas",
    )
    fecha_emision = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
    impuestos = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.EMITIDA)
    uuid_publico = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        db_table = "factura"
        ordering = ["-fecha_emision"]
        permissions = (
            ("ver_facturacion", "Puede ver el módulo de facturación"),
            ("emitir_factura", "Puede emitir facturas"),
            ("registrar_pago_admin", "Puede registrar un pago en nombre del cliente"),
        )
        constraints = [
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0) & models.Q(impuestos__gte=0) & models.Q(total__gte=0),
                name="chk_factura_montos_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.numero} — ${self.total}"

    def clean(self):
        if self.subtotal is not None and self.impuestos is not None and self.total is not None:
            if self.total != self.subtotal + self.impuestos:
                raise ValidationError(
                    {"total": "El total debe ser igual a subtotal + impuestos."}
                )

    def save(self, *args, **kwargs):
        if not self.numero:
            # El cliente nunca envía el número: se genera con contador bloqueado.
            from config.sequences import numero_factura

            using = kwargs.get("using") or self._state.db or "default"
            anio = (self.fecha_emision or timezone.now()).year
            self.numero = numero_factura(anio, using=using)
        super().save(*args, **kwargs)

    @property
    def monto_pagado(self):
        total = self.pagos_factura.filter(estado=PagoFactura.Estado.APROBADO).aggregate(
            s=Sum("monto")
        )["s"]
        return total or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        return (self.total or Decimal("0.00")) - self.monto_pagado

    def recalcular_estado(self):
        if self.estado == self.Estado.ANULADA:
            return
        pagado = self.monto_pagado
        if pagado <= 0:
            nuevo = self.Estado.EMITIDA
        elif pagado < (self.total or 0):
            nuevo = self.Estado.PARCIAL
        else:
            nuevo = self.Estado.PAGADA
        self.transicionar(nuevo)
        self.save(update_fields=["estado"])


class PagoFactura(TransicionMixin, models.Model):
    class Metodo(models.TextChoices):
        EFECTIVO = "efectivo", "Efectivo"
        TRANSFERENCIA = "transferencia", "Transferencia"
        TARJETA = "tarjeta", "Tarjeta"
        PSE = "pse", "PSE"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="pagos_factura")
    monto = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[monto_positivo]
    )
    metodo = models.CharField(max_length=20, choices=Metodo.choices)
    referencia = models.CharField(max_length=100, blank=True)

    TRANSICIONES = {
        Estado.PENDIENTE: {Estado.APROBADO, Estado.RECHAZADO},
        Estado.APROBADO: set(),
        Estado.RECHAZADO: set(),
    }
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.PENDIENTE
    )
    fecha_registro = models.DateTimeField(default=timezone.now)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    evidencia = models.ImageField(
        upload_to=_evidencia_upload_to,
        null=True,
        blank=True,
        help_text="Evidencia fotográfica del comprobante",
        validators=[ArchivoValidator(("png", "jpg", "jpeg"), max_mb=5)],
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    observaciones = models.TextField(blank=True, validators=[MaxLengthValidator(OBSERVACIONES_MAX)])

    class Meta:
        db_table = "pago_factura"
        ordering = ["-fecha_registro"]
        constraints = [
            models.CheckConstraint(check=models.Q(monto__gt=0), name="chk_pago_factura_monto_gt_0"),
        ]
        indexes = [models.Index(fields=["factura", "estado"], name="idx_pago_factura_fac_estado")]

    def __str__(self):
        return f"Pago #{self.pk} {self.factura.numero} — ${self.monto}"
