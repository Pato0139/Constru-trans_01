import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, router, transaction
from django.utils import timezone

from config.state_machine import TransicionMixin
from config.validators import placa_validator, texto_multilinea, texto_sin_simbolos

logger = logging.getLogger(__name__)

# Marcas de vehículos permitidas al registrar/editar la flota. Evita que se
# escriban marcas arbitrarias o sin sentido en el campo "Marca del Vehículo".
MARCAS_VEHICULO = [
    "Agrale",
    "Chevrolet",
    "Dongfeng",
    "FAW",
    "Foton",
    "Ford",
    "Freightliner",
    "Hino",
    "Howo",
    "Hyundai",
    "International",
    "Isuzu",
    "Iveco",
    "JAC",
    "Kenworth",
    "Kia",
    "Mazda",
    "Mercedes-Benz",
    "Mitsubishi",
    "Nissan",
    "Renault",
    "Scania",
    "Shacman",
    "Toyota",
    "Volkswagen",
    "Volvo",
]


class Vehiculo(TransicionMixin, models.Model):
    id_vehiculo = models.AutoField(primary_key=True)
    catalogo = models.ForeignKey(
        "catalogo.Catalogo",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="vehiculos",
        db_column="codigo_catalogo",
    )
    placa = models.CharField(max_length=10, unique=True, validators=[placa_validator])
    marca = models.CharField(max_length=50, validators=[texto_sin_simbolos])
    modelo = models.CharField(max_length=50, validators=[texto_sin_simbolos])
    tipo_vehiculo = models.CharField(max_length=50, validators=[texto_sin_simbolos])
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
    TRANSICIONES = {
        "disponible": {"en_ruta", "mantenimiento", "fuera_de_servicio"},
        "en_ruta": {"disponible", "mantenimiento", "fuera_de_servicio"},
        "mantenimiento": {"disponible", "fuera_de_servicio"},
        "fuera_de_servicio": {"disponible", "mantenimiento"},
    }
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

    @tipo.setter
    def tipo(self, value):
        self.tipo_vehiculo = value

    @property
    def capacidad(self):
        return self.capacidad_carga

    @capacidad.setter
    def capacidad(self, value):
        self.capacidad_carga = value

    @property
    def capacidad_carga_kg(self):
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
        constraints = [
            models.UniqueConstraint(
                fields=["vehiculo"],
                condition=models.Q(fecha_fin__isnull=True),
                name="uniq_active_driver_per_vehicle",
            ),
        ]

    def __str__(self):
        return f"{self.conductor} - {self.vehiculo.placa}"

    def clean(self):
        super().clean()
        if self.vehiculo_id and self.fecha_fin is None:
            db_alias = self._state.db or router.db_for_read(type(self), instance=self)
            qs = ConductorVehiculo.objects.using(db_alias).filter(
                vehiculo_id=self.vehiculo_id, fecha_fin__isnull=True
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exclude(conductor_id=self.conductor_id).exists():
                raise ValidationError("Este vehículo ya está asignado a otro conductor.")

    def save(self, *args, **kwargs):
        db_alias = kwargs.get("using") or self._state.db or router.db_for_write(type(self), instance=self)
        if self.vehiculo_id and self.fecha_fin is None:
            with transaction.atomic(using=db_alias):
                Vehiculo.objects.using(db_alias).select_for_update().filter(pk=self.vehiculo_id).exists()
                asignado_a_otro = (
                    ConductorVehiculo.objects.using(db_alias)
                    .filter(vehiculo_id=self.vehiculo_id, fecha_fin__isnull=True)
                    .exclude(conductor_id=self.conductor_id)
                    .exclude(pk=self.pk)
                    .exists()
                )
                if asignado_a_otro:
                    raise ValidationError("Este vehículo ya está asignado a otro conductor.")
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)


class Entrega(TransicionMixin, models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("en_ruta", "En Ruta"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]

    TRANSICIONES = {
        "pendiente": {"en_ruta", "cancelado"},
        "en_ruta": {"entregado", "pendiente", "cancelado"},
        "entregado": set(),
        "cancelado": set(),
    }

    id_entrega = models.AutoField(primary_key=True)
    pedido = models.ForeignKey("pedidos.Pedido", on_delete=models.CASCADE, related_name="entregas")
    conductor = models.ForeignKey(
        "usuarios.Conductor",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="entregas",
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="entregas"
    )
    fecha_asignacion = models.DateTimeField(null=True, blank=True)
    fecha_salida = models.DateTimeField(null=True, blank=True)
    confirmado_salida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entregas_salida_confirmada",
    )
    fecha_entrega = models.DateTimeField(null=True, blank=True)
    entregado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entregas_finalizadas",
    )
    motivo_cancelacion = models.TextField(blank=True, default="", validators=[texto_multilinea])
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    direccion_entrega = models.CharField(max_length=200, validators=[texto_sin_simbolos])

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

    @property
    def fecha_asignacion_efectiva(self):
        if self.fecha_asignacion:
            return self.fecha_asignacion
        db_alias = self._state.db or "default"
        if self.conductor_id and self.vehiculo_id:
            asig = (
                ConductorVehiculo.objects.using(db_alias)
                .filter(conductor_id=self.conductor_id, vehiculo_id=self.vehiculo_id)
                .order_by("-fecha_asignacion")
                .first()
            )
            if asig and asig.fecha_asignacion:
                return asig.fecha_asignacion
        pago = getattr(self.pedido, "pago_actual", None)
        if pago and getattr(pago, "fecha_revision", None):
            return pago.fecha_revision
        return getattr(self.pedido, "fecha_solicitud", None)

    @property
    def estado_logistico_display(self):
        if self.estado == "pendiente":
            if self.conductor_id and self.vehiculo_id:
                return "Autorizado para despacho"
            if getattr(self.pedido, "estado", "") == "vehiculo_asignado":
                return "Autorizado para despacho"
            if getattr(self.pedido, "estado", "") == "autorizado_despacho":
                return "Autorizado para despacho"
            return "Pendiente"
        return self.get_estado_display()

    def save(self, *args, **kwargs):
        if self.conductor_id and not self.conductor_usuario_id:
            try:
                self.conductor_usuario = self.conductor.usuario
            except AttributeError as exc:
                logger.warning(
                    "No se pudo resolver usuario de entrega en pedido %s: %s",
                    getattr(self.pedido, "codigo_pedido", "?"),
                    exc,
                )
        super().save(*args, **kwargs)


Envio = Entrega


class Novedad(models.Model):
    TIPOS = [
        ("demora", "Demora en entrega"),
        ("clima", "Condiciones climáticas"),
        ("mecanico", "Problemas mecánicos"),
        ("cliente", "Inconveniente con el cliente"),
        ("acceso_vias", "Problemas de acceso o vías"),
        ("mercancia", "Problemas con la mercancía"),
        ("ausencia_cliente", "Ausencia del cliente"),
        ("producto_danado", "Producto dañado"),
        ("cantidad_incorrecta", "Cantidad incorrecta"),
        ("devolucion", "Devolución"),
        ("observacion", "Observación"),
        ("otro", "Otro"),
    ]
    TIPOS_CONDUCTOR_GRUPOS = [
        (
            "Incidencias en ruta y vehículo",
            [
                ("demora", "Demora en entrega"),
                ("clima", "Condiciones climáticas"),
                ("mecanico", "Problemas mecánicos"),
                ("acceso_vias", "Problemas de acceso o vías"),
            ],
        ),
        (
            "Quejas o novedades con el cliente",
            [
                ("cliente", "Queja o inconveniente con el cliente"),
                ("ausencia_cliente", "Ausencia del cliente"),
            ],
        ),
        (
            "Carga y observaciones",
            [
                ("mercancia", "Problemas con la mercancía"),
                ("observacion", "Observación en ruta"),
                ("otro", "Otro"),
            ],
        ),
    ]
    TIPOS_CLIENTE_GRUPOS = [
        (
            "Inconformidad con el pedido o entrega",
            [
                ("demora", "Demora en entrega"),
                ("producto_danado", "Producto dañado"),
                ("cantidad_incorrecta", "Cantidad incorrecta"),
                ("mercancia", "Problemas con la mercancía"),
                ("devolucion", "Solicitud de devolución"),
            ],
        ),
        (
            "Quejas de servicio y otros",
            [
                ("observacion", "Queja o comentario sobre la entrega"),
                ("otro", "Otro"),
            ],
        ),
    ]
    TIPOS_ADMIN_GRUPOS = [
        (
            "Novedades en ruta / Conductor",
            [
                ("demora", "Demora en entrega"),
                ("clima", "Condiciones climáticas"),
                ("mecanico", "Problemas mecánicos"),
                ("acceso_vias", "Problemas de acceso o vías"),
                ("cliente", "Queja o inconveniente con el cliente"),
                ("ausencia_cliente", "Ausencia del cliente"),
            ],
        ),
        (
            "Novedades de pedido / Cliente",
            [
                ("producto_danado", "Producto dañado"),
                ("cantidad_incorrecta", "Cantidad incorrecta"),
                ("mercancia", "Problemas con la mercancía"),
                ("devolucion", "Devolución"),
            ],
        ),
        (
            "Generales",
            [
                ("observacion", "Observación"),
                ("otro", "Otro"),
            ],
        ),
    ]
    TIPOS_PERMITIDOS_POR_ROL = {
        "conductor": {
            "demora",
            "clima",
            "mecanico",
            "acceso_vias",
            "cliente",
            "ausencia_cliente",
            "mercancia",
            "observacion",
            "otro",
        },
        "cliente": {
            "demora",
            "producto_danado",
            "cantidad_incorrecta",
            "mercancia",
            "devolucion",
            "observacion",
            "otro",
        },
        "admin": {clave for clave, _ in TIPOS},
    }

    @classmethod
    def get_grupos_tipos_por_rol(cls, rol):
        if rol == "conductor":
            return cls.TIPOS_CONDUCTOR_GRUPOS
        if rol == "cliente":
            return cls.TIPOS_CLIENTE_GRUPOS
        return cls.TIPOS_ADMIN_GRUPOS

    @classmethod
    def get_tipos_planos_por_rol(cls, rol):
        grupos = cls.get_grupos_tipos_por_rol(rol)
        return [item for _, opciones in grupos for item in opciones]
    ESTADOS = [
        ("abierta", "Abierta"),
        ("en_atencion", "En atención"),
        ("cerrada", "Cerrada"),
        ("rechazada", "Rechazada"),
    ]
    id_novedad = models.BigAutoField(primary_key=True)

    entrega = models.ForeignKey(
        "logistica.Entrega", on_delete=models.PROTECT, related_name="novedades"
    )

    tipo = models.CharField(max_length=30, choices=TIPOS)
    descripcion = models.TextField(validators=[texto_multilinea])
    solucion = models.TextField(blank=True, default="", validators=[texto_multilinea])
    evidencia = models.ImageField(upload_to="novedades/%Y/%m/", null=True, blank=True)
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

    @property
    def rol_reportante(self):
        return getattr(self.reportado_por, "rol", "admin") or "admin"

    @property
    def rol_reportante_label(self):
        return {
            "conductor": "Conductor",
            "cliente": "Cliente",
            "admin": "Administrador",
        }.get(self.rol_reportante, self.rol_reportante.title())

    @property
    def ultima_respuesta_admin(self):
        """Devuelve la última respuesta registrada por administración para esta novedad."""
        seguimientos = list(self.seguimientos.all())
        for seg in seguimientos:
            respuesta = getattr(seg, "respuesta", None)
            if respuesta and respuesta.texto:
                return respuesta.texto
        for seg in seguimientos:
            if getattr(seg.atendido_por, "rol", "") == "admin" and seg.comentario:
                return seg.comentario
        return ""

    @property
    def respuesta_admin(self):
        return self.ultima_respuesta_admin

    def cerrar(self):
        self.estado = "cerrada"
        self.fecha_cierre = timezone.now()
        self.save(update_fields=["estado", "fecha_cierre"])


class Seguimiento(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("respondida", "Respondida"),
        ("escalado", "Escalado"),
    ]
    id_seguimiento = models.BigAutoField(primary_key=True)
    novedad = models.ForeignKey(Novedad, on_delete=models.CASCADE, related_name="seguimientos")
    atendido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="seguimientos_atendidos",
    )
    fecha_seguimiento = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(validators=[texto_multilinea])
    estado = models.CharField(max_length=15, choices=ESTADOS, default="pendiente")

    class Meta:
        db_table = "seguimiento"
        permissions = (("responder_seguimiento", "Puede responder seguimientos"),)
        ordering = ["-fecha_seguimiento"]

    def __str__(self):
        return f"Seguimiento #{self.id_seguimiento} de Novedad {self.novedad_id}"


class RespuestaSeguimiento(models.Model):
    ESTADOS = [
        ("aceptada", "Aceptada"),
        ("rechazada", "Rechazada"),
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
    texto = models.TextField(validators=[texto_multilinea])
    estado = models.CharField(max_length=15, choices=ESTADOS, default="aceptada")

    class Meta:
        db_table = "respuesta_seguimiento"
        ordering = ["-fecha_respuesta"]

    def __str__(self):
        return f"Respuesta a {self.seguimiento}"
