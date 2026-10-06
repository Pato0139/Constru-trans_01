from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True)
    catalogo = models.ForeignKey(
        "catalogo.Catalogo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehiculos",
        db_column="codigo_catalogo",
    )
    placa = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    tipo_vehiculo = models.CharField(max_length=50)
    capacidad_carga = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    ESTADOS_VEHICULO = [
        ("disponible", "Disponible"),
        ("en_ruta", "En Ruta"),
        ("mantenimiento", "Mantenimiento"),
        ("fuera_de_servicio", "Fuera de Servicio"),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS_VEHICULO, default="disponible")

    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = "vehiculo"
        constraints = [
            models.CheckConstraint(
                check=models.Q(capacidad_carga__gt=0),
                name="chk_vehiculo_capacidad_carga_gt_0",
            ),
        ]

    def __str__(self):
        return f"{self.placa} ({self.marca} {self.modelo})"

    @property
    def id(self):
        return self.id_vehiculo

    @property
    def tipo(self):
        return self.tipo_vehiculo

    @property
    def capacidad(self):
        return self.capacidad_carga

    @property
    def conductor_actual(self):
        asignacion = (
            self.asignaciones_conductor.filter(fecha_fin__isnull=True)
            .select_related("conductor__usuario")
            .order_by("-fecha_asignacion")
            .first()
        )
        return asignacion.conductor.usuario if asignacion else None


class ConductorVehiculo(models.Model):
    conductor = models.ForeignKey(
        "usuarios.Conductor", on_delete=models.CASCADE, related_name="asignaciones_vehiculo"
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.CASCADE, related_name="asignaciones_conductor"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conductor_vehiculo"
        unique_together = ("conductor", "vehiculo", "fecha_asignacion")
        ordering = ["-fecha_asignacion"]

    def __str__(self):
        return f"{self.conductor} - {self.vehiculo.placa}"


class Entrega(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("en_ruta", "En Ruta"), ("entregado", "Entregado")]

    id_entrega = models.AutoField(primary_key=True)
    pedido = models.ForeignKey("pedidos.Pedido", on_delete=models.CASCADE, related_name="entregas")
    conductor = models.ForeignKey(
        "usuarios.Conductor", on_delete=models.PROTECT, related_name="entregas"
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="entregas"
    )
    fecha_salida = models.DateTimeField(null=True, blank=True)
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    direccion_entrega = models.CharField(max_length=200)

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

    entrega = models.ForeignKey(
        "logistica.Entrega", on_delete=models.PROTECT, related_name="novedades"
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
