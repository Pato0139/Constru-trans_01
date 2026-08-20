import uuid

from django.db import models
from django.conf import settings
from django.db import models
from django.db.models import Q


class Installation(models.Model):
    instance_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_id = models.CharField(max_length=64, blank=True, default="")
    activated_at = models.DateTimeField(null=True, blank=True)
    last_validated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    license_token = models.TextField(blank=True, default="")
    build_hash = models.CharField(max_length=64, blank=True, default="")
    manifest_hash = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "licensing_installation"

    def __str__(self):
        return f"Installation {self.instance_id} ({self.status})"
    
# =========================================================================
# Licencias por USUARIO (complementan Installation, no la reemplazan)
# =========================================================================

class Licencia(models.Model):
    ESTADOS = [
        ("activa", "Activa"),
        ("expirada", "Expirada"),
        ("revocada", "Revocada"),
    ]

    codigo = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, default="")

    permisos = models.ManyToManyField(
        "auth.Permission",
        related_name="licencias",
        blank=True,
        help_text="Permisos Django (app.codename) que entrega esta licencia.",
    )

    fecha_emision = models.DateTimeField()
    fecha_expiracion = models.DateTimeField()
    estado = models.CharField(max_length=15, choices=ESTADOS, default="activa")

    # Datos del archivo .lic cifrado con AES-GCM-256
    archivo_cifrado_nonce = models.BinaryField()
    archivo_cifrado_ciphertext = models.BinaryField()
    archivo_cifrado_aad = models.BinaryField(default=b"constru-trans-lic-v1")

    # KDF Argon2id independiente del login del usuario
    password_hash = models.CharField(max_length=128)
    password_salt = models.BinaryField()
    password_kdf_params = models.JSONField(default=dict)
    rotaciones_password = models.PositiveIntegerField(default=0)
    ultima_rotacion_password = models.DateTimeField(null=True, blank=True)

    revocada_en = models.DateTimeField(null=True, blank=True)
    revocada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="licencias_revocadas",
    )
    motivo_revocacion = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "licencia"
        indexes = [models.Index(fields=["estado", "fecha_expiracion"])]

    def __str__(self):
        return f"{self.codigo} · {self.estado}"

    @property
    def esta_vigente(self) -> bool:
        from django.utils.timezone import now
        return self.estado == "activa" and self.fecha_expiracion > now()


class UsuarioLicencia(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="licencias",
    )
    licencia = models.ForeignKey(
        Licencia,
        on_delete=models.PROTECT,
        related_name="asignaciones",
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_desasignacion = models.DateTimeField(null=True, blank=True)
    motivo_desasignacion = models.TextField(blank=True, default="")
    asignada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, on_delete=models.SET_NULL,
        related_name="licencias_asignadas_por",
    )
    ip_asignacion = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = "usuario_licencia"
        constraints = [
            models.UniqueConstraint(
                fields=["usuario", "licencia"],
                condition=Q(fecha_desasignacion__isnull=True),
                name="uq_usuario_licencia_vigente",
            )
        ]

    def __str__(self):
        return f"{self.usuario} ← {self.licencia.codigo}"


class AuditoriaLicencia(models.Model):
    ACCIONES = [
        ("LICENCIA_CREADA", "Licencia creada"),
        ("LICENCIA_ASIGNADA", "Licencia asignada"),
        ("LICENCIA_DESASIGNADA", "Licencia desasignada"),
        ("LICENCIA_REVOCADA", "Licencia revocada"),
        ("LICENCIA_RENOVADA", "Licencia renovada"),
        ("PASSWORD_ROTADO", "Password del archivo rotado"),
        ("PERMISO_DENEGADO", "Acceso denegado por permiso"),
        ("INTENTO_SWITCH_ROLE", "Intento de cambio libre de rol"),
    ]
    licencia = models.ForeignKey(
        Licencia, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="auditoria",
    )
    usuario_afectado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, on_delete=models.SET_NULL,
        related_name="eventos_licencia",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, on_delete=models.SET_NULL,
        related_name="cambios_licencia_realizados",
    )
    accion = models.CharField(max_length=30, choices=ACCIONES)
    detalle = models.TextField(blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    exitosa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "licencia_auditoria"
        ordering = ["-created_at"]
