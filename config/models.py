from django.conf import settings
from django.db import models
from django.utils import timezone


class BloqueoIP(models.Model):

    TIPOS_BLOQUEO = (
        ("unauthorized_access", "Acceso no autorizado repetido"),
        ("brute_force", "Fuerza bruta (intentos login)"),
        ("tampering", "Manipulación de licencia/sistema"),
        ("manual", "Bloqueo manual por administrador"),
    )

    ip = models.GenericIPAddressField(db_index=True, verbose_name="Dirección IP")
    tipo = models.CharField(max_length=32, choices=TIPOS_BLOQUEO, default="unauthorized_access")
    motivo = models.TextField(blank=True, default="")
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Si es nulo, el bloqueo es permanente.",
    )
    activo = models.BooleanField(default=True, db_index=True)
    intentos_asociados = models.PositiveIntegerField(default=0)
    bloqueado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        db_table = "bloqueo_ip"
        ordering = ["-creado_en"]
        constraints = [
            models.UniqueConstraint(
                fields=["ip", "activo"],
                condition=models.Q(activo=True),
                name="uq_bloqueo_ip_activo",
            ),
        ]

    def __str__(self):
        estado = "activo" if self.activo else "inactivo"
        return f"{self.ip} ({estado}) - {self.tipo}"

    @property
    def esta_vigente(self):
        if not self.activo:
            return False
        if self.expira_en is None:
            return True
        return timezone.now() <= self.expira_en

    @classmethod
    def obtener_bloqueo_vigente(cls, ip):
        if not ip:
            return None
        try:
            from django.db import OperationalError as _OpErr
            from django.db import ProgrammingError as _ProgErr

            return cls.objects.get(ip=ip, activo=True)
        except cls.DoesNotExist:
            return None
        except (_ProgErr, _OpErr, Exception) as exc:
            import logging as _log

            _log.getLogger(__name__).warning(
                "No se pudo consultar BloqueoIP (tabla ausente o error de BD): %s", exc
            )
            return None


class SecurityEvent(models.Model):
    """
    Registro de eventos de seguridad: accesos no autorizados, alertas, etc.
    """

    GRAVEDAD = (
        ("info", "Informativo"),
        ("warning", "Advertencia"),
        ("high", "Alta"),
        ("critical", "Crítica"),
    )

    TIPOS_EVENTO = (
        ("unauthorized_access", "Acceso no autorizado"),
        ("role_violation", "Intento de salto de rol"),
        ("license_tamper", "Manipulación de licencia"),
        ("ip_blocked", "IP bloqueada"),
        ("login_failed", "Login fallido"),
        ("login_ok", "Login exitoso"),
        ("admin_switch", "Superadmin cambió de panel"),
        ("security_warning", "Advertencia de seguridad"),
    )

    tipo = models.CharField(max_length=40, choices=TIPOS_EVENTO, db_index=True)
    gravedad = models.CharField(max_length=10, choices=GRAVEDAD, default="warning")
    ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="eventos_seguridad",
    )
    username_str = models.CharField(max_length=150, blank=True, default="", db_index=True)
    path = models.CharField(max_length=512, blank=True, default="")
    metodo_http = models.CharField(max_length=10, blank=True, default="")
    user_agent = models.CharField(max_length=512, blank=True, default="")
    referer = models.CharField(max_length=512, blank=True, default="")
    detalles = models.JSONField(null=True, blank=True, default=dict)
    creado_en = models.DateTimeField(auto_now_add=True, db_index=True)
    advertencia_mostrada = models.BooleanField(default=False)

    class Meta:
        db_table = "security_event"
        ordering = ["-creado_en"]
        indexes = [
            models.Index(fields=["ip", "creado_en"]),
            models.Index(fields=["tipo", "creado_en"]),
        ]

    def __str__(self):
        return f"[{self.creado_en:%d/%m/%Y %H:%M}] {self.tipo} ({self.ip or '-'})"


class Historial(models.Model):
    ACCIONES = [
        ("crear", "Crear"),
        ("editar", "Editar"),
        ("eliminar", "Eliminar"),
        ("login", "Inicio de sesión"),
        ("logout", "Cierre de sesión"),
        ("otro", "Otro"),
    ]

    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historial_core",
        verbose_name="Usuario",
    )
    accion = models.CharField(max_length=20, choices=ACCIONES, verbose_name="Acción")
    tabla = models.CharField(max_length=50, blank=True, null=True, verbose_name="Tabla")
    registro_id = models.IntegerField(
        blank=True, null=True, verbose_name="ID del Registro"
    )
    fecha = models.DateTimeField(default=timezone.now, verbose_name="Fecha")
    ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")

    sincronizado = models.BooleanField(default=False)
    modulo = models.CharField(max_length=50, blank=True, null=True, verbose_name="Módulo")
    elemento_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="ID Legacy")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción detallada")
    fecha_hora = models.DateTimeField(default=timezone.now, blank=True, null=True, verbose_name="Fecha y Hora")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Legacy")

    class Meta:
        verbose_name = "Historial de Actividad"
        verbose_name_plural = "Historial de Actividades"
        ordering = ["-fecha"]
        db_table = "historial_core"

    def __str__(self):
        return f"{self.usuario} - {self.accion} - {self.tabla or self.modulo} ({self.fecha})"

    def save(self, *args, **kwargs):
        if not self.modulo and self.tabla:
            self.modulo = self.tabla
        if not self.tabla and self.modulo:
            self.tabla = self.modulo
        if not self.elemento_id and self.registro_id is not None:
            self.elemento_id = str(self.registro_id)
        if self.registro_id is None and self.elemento_id and self.elemento_id.isdigit():
            self.registro_id = int(self.elemento_id)
        if not self.ip_address and self.ip:
            self.ip_address = self.ip
        if not self.ip and self.ip_address:
            self.ip = self.ip_address
        if self.fecha_hora is None and self.fecha:
            self.fecha_hora = self.fecha
        if self.fecha is None and self.fecha_hora:
            self.fecha = self.fecha_hora
        super().save(*args, **kwargs)


class Reporte(models.Model):
    TIPOS = [
        ("inventario", "Inventario"),
        ("ventas", "Ventas"),
        ("compras", "Compras"),
        ("entregas", "Entregas"),
        ("financiero", "Financiero"),
    ]
    ESTADOS = [
        ("generado", "Generado"),
        ("archivado", "Archivado"),
        ("eliminado", "Eliminado"),
    ]

    numero_reporte = models.CharField(max_length=20, primary_key=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    fecha_generada = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default="generado")
    descripcion = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reporte_usuario",
    )
    archivo_pdf = models.FileField(upload_to="reportes/", null=True, blank=True)

    class Meta:
        ordering = ["-fecha_generada"]
        db_table = "reporte_core"

    def __str__(self):
        return f"Reporte {self.numero_reporte}"


class HistorialReporte(models.Model):
    codigo_historia = models.CharField(max_length=20, primary_key=True)
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name="historial")
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()

    class Meta:
        ordering = ["-fecha_reporte"]
        db_table = "historial_reporte_core"

    def __str__(self):
        return f"Historial {self.codigo_historia}"
