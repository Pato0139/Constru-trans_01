from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from facturacion.models import Factura
from ordenes.models import Pedido


# =====================================================================
# PAGO
# =====================================================================
class Pago(models.Model):
    id_pago = models.AutoField(primary_key=True)
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="pagos")
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
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = "pago"

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
    metodo_pago = models.CharField(max_length=80, blank=True, default="")
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
