from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Pago(models.Model):
    METODOS = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia bancaria"),
        ("tarjeta", "Tarjeta"),
        ("pse", "PSE"),
    ]
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("aprobado", "Aprobado"),
        ("rechazado", "Rechazado"),
    ]

    id = models.BigAutoField(primary_key=True)
    pedido = models.ForeignKey(
        "ordenes.Pedido", on_delete=models.PROTECT, related_name="pagos"
    )
    monto = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    metodo = models.CharField(max_length=20, choices=METODOS)
    referencia = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=12, choices=ESTADOS, default="pendiente")
    fecha_registro = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "pago"
        ordering = ["-fecha_registro"]
        indexes = [
            models.Index(fields=["estado", "fecha_registro"]),
            models.Index(fields=["pedido", "estado"]),
        ]

    def __str__(self):
        return f"Pago #{self.pk} - Pedido #{self.pedido_id}"
