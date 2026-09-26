from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def comprobante_upload_to(instance, filename):
    pedido_id = getattr(instance, "pedido_id", None) or "sin_pedido"
    return f"comprobantes/pedido_{pedido_id}/{filename}"


class Pago(models.Model):
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
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default=PENDIENTE, db_column="estado_pago")
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
    observaciones = models.TextField(blank=True, db_column="motivo_rechazo")

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
        if self.requiere_comprobante() and not self.comprobante:
            raise ValidationError(
                {"comprobante": "Este método de pago requiere comprobante."}
            )

    def marcar_revision(self, *, estado, revisor, observaciones=""):
        if estado not in (self.APROBADO, self.RECHAZADO):
            raise ValueError("La revisión solo admite aprobado o rechazado.")
        self.estado = estado
        self.revisado_por = revisor
        self.observaciones = observaciones or ""
        self.fecha_revision = timezone.now()
