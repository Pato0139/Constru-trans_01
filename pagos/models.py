from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from facturacion.models import Factura
from ordenes.models import Pedido


# =====================================================================
# PAGO  (MER: #id_pago *id_factura -monto -fecha *codigo_metodo_pago
#        -referencia *registrado_por_id sincronizado)
# =====================================================================
class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="pagos", db_column="id_factura")
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    fecha = models.DateTimeField(auto_now_add=True)
    codigo_metodo_pago = models.ForeignKey(
        "usuarios.MetodoPago", db_column="codigo_metodo_pago", on_delete=models.PROTECT
    )

    # NO se toca
    referencia = models.CharField(max_length=100, blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="pagos_registrados", db_column="registrado_por_id"
    )
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = "pago"
        constraints = [
            models.CheckConstraint(
                check=models.Q(monto__gt=0),
                name="chk_pago_monto_gt_0",
            ),
        ]

    def __str__(self):
        return f"Pago {self.id_pago} - ${self.monto}"


class PagoPedido(models.Model):
    ESTADOS_PAGO = [
        ("pendiente", "Pendiente"),
        ("en_revision", "En revisión"),
        ("pago aprobado", "Pago aprobado"),
        ("pago rechazado", "Pago rechazado"),
        ("contra_entrega", "Contra entrega"),
    ]

    id_pago_pedido = models.AutoField(primary_key=True)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="pagos_pedido")
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos_pedido",
    )
    metodo_pago_fk = models.ForeignKey(
        "usuarios.MetodoPago",
        on_delete=models.PROTECT,
        db_column="codigo_metodo_pago",
        null=True,
        blank=True,
        related_name="pagos_pedido",
    )
    metodo_pago = models.CharField(max_length=80, blank=True, default="", db_column="metodo_pago_legacy")
    estado_pago = models.CharField(
        max_length=30,
        choices=ESTADOS_PAGO,
        default="pendiente",
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    referencia = models.CharField(max_length=120, blank=True, default="")
    comprobante = models.FileField(
        upload_to="comprobantes_pagos/%Y/%m/%d/",
        blank=True,
        null=True,
    )
    motivo_rechazo = models.TextField(blank=True, default="")
    historial = models.JSONField(default=list, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "pago_pedido"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Pago pedido {self.pedido_id} - {self.estado_pago}"

    def save(self, *args, **kwargs):
        if self.metodo_pago_fk_id and not self.metodo_pago:
            try:
                self.metodo_pago = self.metodo_pago_fk.metodo
            except Exception:
                pass
        elif self.metodo_pago and not self.metodo_pago_fk_id:
            try:
                from usuarios.models import MetodoPago
                db_alias = kwargs.get("using") or self._state.db or "default"
                mp = MetodoPago.objects.using(db_alias).filter(
                    models.Q(metodo=self.metodo_pago)
                    | models.Q(codigo_metodo_pago=self.metodo_pago)
                ).first()
                if mp:
                    self.metodo_pago_fk = mp
            except Exception:
                pass
        super().save(*args, **kwargs)

    def agregar_historial(self, texto):
        self.historial = list(self.historial or []) + [texto]
        self.save(update_fields=["historial", "fecha_actualizacion"])


@receiver(post_save, sender=Pago)
def actualizar_estado_factura(sender, instance, created, **kwargs):
    if created:
        factura = instance.factura
        if factura.saldo_pendiente <= 0 and factura.estado != "pagada":
            factura.estado = "pagada"
            factura.save()
