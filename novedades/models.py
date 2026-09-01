from django.conf import settings
from django.db import models
from django.utils import timezone


class Novedad(models.Model):
    TIPOS = [
        ("demora",              "Demora en entrega"),
        ("producto_danado",     "Producto dañado"),
        ("cantidad_incorrecta", "Cantidad incorrecta"),
        ("devolucion",          "Devolución"),
        ("observacion",         "Observación"),
    ]
    ESTADOS = [
        ("abierta",     "Abierta"),
        ("en_atencion", "En atención"),
        ("cerrada",     "Cerrada"),
        ("rechazada",   "Rechazada"),
    ]
    id_novedad = models.BigAutoField(primary_key=True)

    # ANTES: pedido = models.ForeignKey("ordenes.Pedido", on_delete=models.CASCADE, related_name="novedades")
    # AHORA: la novedad pertenece a un envío/entrega concreto, no al pedido general.
    # El pedido se obtiene mediante novedad.entrega.pedido
    entrega = models.ForeignKey(
        "ordenes.Entrega", on_delete=models.PROTECT, related_name="novedades"
    )

    tipo = models.CharField(max_length=30, choices=TIPOS)
    descripcion = models.TextField()
    estado = models.CharField(max_length=15, choices=ESTADOS, default="abierta")
    fecha_generada = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    reportado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="novedades_reportadas"
    )
    class Meta:
        db_table = "novedad"
        permissions = (("registrar_novedad", "Puede registrar novedades"),)
        ordering = ["-fecha_generada"]
        indexes = [models.Index(fields=["estado"]), models.Index(fields=["tipo"])]
    def __str__(self):
        return f"Novedad #{self.id_novedad} - {self.tipo} ({self.estado})"

    @property
    def pedido(self):
        """Acceso de conveniencia: novedad.pedido -> novedad.entrega.pedido"""
        return self.entrega.pedido

    def cerrar(self):
        self.estado = "cerrada"
        self.fecha_cierre = timezone.now()
        self.save(update_fields=["estado", "fecha_cierre"])


class Seguimiento(models.Model):
    ESTADOS = [
        ("pendiente",  "Pendiente"),
        ("respondida", "Respondida"),
        ("escalado",   "Escalado"),
    ]
    id_seguimiento = models.BigAutoField(primary_key=True)
    novedad = models.ForeignKey(Novedad, on_delete=models.CASCADE, related_name="seguimientos")
    atendido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="seguimientos_atendidos",
    )
    fecha_seguimiento = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField()
    estado = models.CharField(max_length=15, choices=ESTADOS, default="pendiente")
    class Meta:
        db_table = "seguimiento"
        permissions = (("responder_seguimiento", "Puede responder seguimientos"),)
        ordering = ["-fecha_seguimiento"]
    def __str__(self):
        return f"Seguimiento #{self.id_seguimiento} de Novedad {self.novedad_id}"


class RespuestaSeguimiento(models.Model):
    """Respuesta 1:1 obligatoria a cada seguimiento (cierra el bucle)."""
    ESTADOS = [
        ("aceptada",   "Aceptada"),
        ("rechazada",  "Rechazada"),
        ("en_gestion", "En gestión"),
    ]
    id_respuesta = models.BigAutoField(primary_key=True)
    seguimiento = models.OneToOneField(
        Seguimiento, on_delete=models.CASCADE, related_name="respuesta"
    )
    redactada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="respuestas_redactadas"
    )
    fecha_respuesta = models.DateTimeField(auto_now_add=True)
    texto = models.TextField()
    estado = models.CharField(max_length=15, choices=ESTADOS, default="aceptada")
    class Meta:
        db_table = "respuesta_seguimiento"
        ordering = ["-fecha_respuesta"]
    def __str__(self):
        return f"Respuesta a {self.seguimiento}"