from django.conf import settings
from django.db import models
from django.utils import timezone


class BloqueoIP(models.Model):
    """
    Bloqueo permanente o temporal por IP para intentos repetidos de intrusión.
    """

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
            from django.db import OperationalError as _OpErr, ProgrammingError as _ProgErr

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
