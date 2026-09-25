from django.contrib.auth.models import AbstractUser, UserManager
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from django.core.files.storage import default_storage
import datetime
import uuid
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def foto_perfil_upload_path(instance, filename):
    extension = Path(filename or "avatar.jpg").suffix.lower() or ".jpg"
    user_segment = instance.pk if instance and instance.pk is not None else "nuevo"
    return f"perfiles/usuarios/usuario_{user_segment}/{uuid.uuid4().hex}{extension}"

def validar_fecha_no_pasada(value):
    today = now().date()
    if isinstance(value, datetime.datetime):
        value = value.date()
    if value and value < today:
        raise ValidationError("La fecha no puede ser en el pasado.")

numeric_and_space_validator = RegexValidator(
    regex=r"^[0-9\s]*$", message="Solo se admiten números y espacios.", code="invalid_numeric_space"
)



# =====================================================================
# USUARIO
# =====================================================================
class UsuarioManager(UserManager):
    def create_user(self, username=None, email=None, password=None, **extra_fields):
        username = username or email
        extra_fields.setdefault("tipo_documento", "CC")
        extra_fields.setdefault("documento", str(uuid.uuid4().int)[:20])
        return super().create_user(username, email, password, **extra_fields)


class Usuario(AbstractUser):
    TIPOS_DOCUMENTO = [
        ("CC", "Cédula de Ciudadanía"),
        ("CE", "Cédula de Extranjería"),
        ("PA", "Pasaporte"),
        ("PEP", "Permiso Especial de Permanencia"),
        ("PPT", "Permiso por Protección Temporal"),
        ("NIT", "Número de Identificación Tributaria"),
    ]
    ESTADO_USUARIO = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
        ("suspendido", "Suspendido"),
    ]
    ROLES = [
        ("admin", "Admin"),
        ("cliente", "Cliente"),
        ("conductor", "Conductor"),
        ("empleado", "Empleado"),
    ]

    nombres = models.CharField(max_length=200)
    apellidos = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    documento = models.CharField(max_length=20, validators=[numeric_and_space_validator])

    rol = models.CharField(max_length=50, choices=ROLES)

    # NO se toca
    tipo_documento = models.CharField(max_length=5, choices=TIPOS_DOCUMENTO)
    estado = models.CharField(max_length=15, choices=ESTADO_USUARIO, default="activo")
    foto_perfil = models.FileField(
        upload_to=foto_perfil_upload_path,
        null=True,
        blank=True,
    )
    sincronizado = models.BooleanField(default=False)

    objects = UsuarioManager()
    
    # Bloqueo por intentos fallidos
    intentos_fallidos = models.IntegerField(default=0, help_text="Número de intentos fallidos de inicio de sesión")
    bloqueado_hasta = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora hasta la que está bloqueado el usuario")
    nivel_bloqueo = models.IntegerField(default=0, help_text="0: sin bloqueo, 1: 5 minutos, 2: 24 horas")

    class Meta:
        db_table = "usuario"
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_documento", "documento"],
                name="uq_usuario_tipo_documento_documento",
            ),
        ]

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.rol})"

    @property
    def contraseña(self):
        return self.password

    @property
    def user(self):
        return self

    @property
    def usuario(self):
        """Compatibilidad con vistas antiguas que usan request.user.usuario."""
        return self

    @property
    def iniciales(self):
        partes = self.nombres.split()
        return "".join([p[0].upper() for p in partes[:2]]) or "?"

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def nombre_mostrar(self):
        return self.nombre_completo or self.email or self.username or f"Usuario #{self.pk}"

    @property
    def documento_mostrar(self):
        return self.documento or "Sin documento"

    @property
    def avatar_url(self):
        if not self.foto_perfil or not self.foto_perfil.name:
            return None
        try:
            if default_storage.exists(self.foto_perfil.name):
                return self.foto_perfil.url
        except Exception as exc:
            logger.warning("No fue posible resolver avatar_url para usuario %s: %s", self.pk, exc)
            return None
        return None

    @property
    def color_avatar(self):
        colores = [
            "#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6",
            "#EC4899", "#06B6D4", "#84CC16", "#F97316", "#6366F1",
        ]
        return colores[self.id % len(colores)] if self.id else colores[0]

    def ensure_profile_for_role(self, using=None):
        """Crea o devuelve el perfil asociado al rol del usuario."""
        if self.rol == "cliente":
            from clientes.models import Cliente
            return Cliente.ensure_for_user(self, using=using)
        if self.rol == "conductor":
            return Conductor.ensure_for_user(self, using=using)
        return None

    @property
    def es_admin(self):
        return self.rol == "admin"

    @property
    def es_conductor(self):
        return self.rol == "conductor"

    @property
    def es_cliente(self):
        return self.rol == "cliente"

    @property
    def es_empleado(self):
        return self.rol == "empleado"

    @property
    def es_superadmin(self):
        return bool(getattr(self, "is_superuser", False)) or self.pk == 1

    @property
    def conductor_profile(self):
        try:
            return self.perfil_conductor
        except Conductor.DoesNotExist:
            return None

    @property
    def nombre(self):
        return self.nombres

    @property
    def vehiculo_actual(self):
        if self.rol != "conductor":
            return None
        try:
            return self.perfil_conductor.vehiculo_actual
        except Conductor.DoesNotExist:
            return None

    @property
    def vehiculo_asignado(self):
        return self.vehiculo_actual

    def esta_bloqueado(self):
        """Verifica si el usuario está bloqueado actualmente."""
        from django.utils import timezone
        if self.bloqueado_hasta and timezone.now() < self.bloqueado_hasta:
            return True
        return False

    def registrar_intento_fallido(self):
        """Registra un intento fallido y bloquea el usuario si es necesario."""
        from django.utils import timezone
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= 3 and self.nivel_bloqueo < 1:
            self.nivel_bloqueo = 1
            self.bloqueado_hasta = timezone.now() + timezone.timedelta(minutes=5)
        elif self.intentos_fallidos >= 6 and self.nivel_bloqueo < 2:
            self.nivel_bloqueo = 2
            self.bloqueado_hasta = timezone.now() + timezone.timedelta(days=1)
        self.save()

    def reiniciar_intentos(self):
        """Reinicia los intentos fallidos después de un inicio de sesión exitoso."""
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        self.nivel_bloqueo = 0
        self.save()

    def obtener_tiempo_restante_bloqueo(self):
        """Devuelve el tiempo restante de bloqueo en un formato legible."""
        from django.utils import timezone
        if not self.esta_bloqueado():
            return None
        tiempo_restante = self.bloqueado_hasta - timezone.now()
        if tiempo_restante.days > 0:
            return f"{tiempo_restante.days} día(s)"
        horas, resto = divmod(tiempo_restante.seconds, 3600)
        minutos, _ = divmod(resto, 60)
        if horas > 0:
            return f"{horas} hora(s) y {minutos} minuto(s)"
        return f"{minutos} minuto(s)"

    def save(self, *args, **kwargs):
        first_name_max = self._meta.get_field("first_name").max_length
        last_name_max = self._meta.get_field("last_name").max_length

        if self.nombres and not self.first_name:
            self.first_name = self.nombres[:first_name_max]
        elif not self.nombres and self.first_name:
            self.nombres = self.first_name

        if self.apellidos and not self.last_name:
            self.last_name = self.apellidos[:last_name_max]
        elif not self.apellidos and self.last_name:
            self.apellidos = self.last_name

        # SINCRONIZACIÓN CRÍTICA: ModelBackend usa self.is_active para autenticar.
        # El campo custom `estado` es el fuente de verdad para el proyecto.
        if self.estado in {"activo", "inactivo", "suspendido"}:
            self.is_active = self.estado == "activo"
        elif self.is_active is not None:
            # Si sólo se tocó is_active, retro-alimenta estado (compatibilidad)
            self.estado = "activo" if self.is_active else "inactivo"

        super().save(*args, **kwargs)

        if self.rol:
            try:
                db_alias = kwargs.get("using") or self._state.db or "default"
                with transaction.atomic(using=db_alias):
                    rol_obj, _ = Rol.objects.using(db_alias).get_or_create(
                        nombre_rol=self.rol,
                        defaults={"activo": True},
                    )
                    UsuarioRol.objects.using(db_alias).get_or_create(
                        usuario=self,
                        rol=rol_obj,
                        defaults={"activo": True},
                    )
            except IntegrityError as exc:
                logger.warning("Conflicto de integridad sincronizando rol de usuario %s: %s", self.pk, exc)
            except DatabaseError as exc:
                logger.error("Fallo de BD sincronizando rol de usuario %s: %s", self.pk, exc)


# =====================================================================
# ROL
# =====================================================================
class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre_rol = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "rol"
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.nombre_rol


class UsuarioRol(models.Model):
    id_usuario_rol = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="usuario_roles")
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name="usuarios")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_revocacion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "usuario_rol"
        unique_together = ("usuario", "rol")
        verbose_name = "Usuario Rol"
        verbose_name_plural = "Usuario Roles"

    def __str__(self):
        return f"{self.usuario.nombres} - {self.rol.nombre_rol}"


class EPS(models.Model):
    codigo_eps = models.CharField(max_length=20, primary_key=True)
    numero_seguro = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField()

    class Meta:
        db_table = "eps"
        verbose_name_plural = "EPS"

    def __str__(self):
        return f"EPS {self.codigo_eps}"


class Conductor(models.Model):
    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, primary_key=True, related_name="perfil_conductor"
    )
    numero_licencia = models.CharField(max_length=50, unique=True)
    categoria_licencia = models.CharField(max_length=10)
    fecha_vencimiento_licencia = models.DateField(validators=[validar_fecha_no_pasada])
    telefono_empresarial = models.CharField(max_length=20, blank=True)

    ESTADO_CONDUCTOR = [("activo", "Activo"), ("inactivo", "Inactivo")]
    estado = models.CharField(max_length=15, choices=ESTADO_CONDUCTOR, default="activo")
    fecha_ingreso = models.DateField(null=True, blank=True)
    eps = models.ForeignKey(EPS, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "conductor"

    def __str__(self):
        return f"Conductor: {self.usuario.nombres}"

    @classmethod
    def ensure_for_user(cls, user, using=None, defaults=None):
        """Crea o devuelve el perfil de conductor para un usuario persistido."""
        if user is None:
            raise ValueError("Se requiere un usuario válido para crear el perfil de conductor.")

        if not getattr(user, "pk", None):
            raise ValueError(
                "El usuario debe existir en base de datos antes de crear el perfil de conductor."
            )

        db_alias = using or getattr(getattr(user, "_state", None), "db", None) or "default"
        user_for_profile = cls._resolve_user_for_db(user, db_alias)
        if user_for_profile is None:
            raise ValueError("No fue posible resolver un usuario válido para el perfil de conductor.")

        profile_defaults = {
            "numero_licencia": f"PEND-{user_for_profile.pk}",
            "categoria_licencia": "N/A",
            "fecha_vencimiento_licencia": now().date(),
            "estado": "activo",
        }
        if defaults:
            profile_defaults.update(defaults)

        with transaction.atomic(using=db_alias):
            return cls.objects.using(db_alias).get_or_create(
                usuario=user_for_profile,
                defaults=profile_defaults,
            )

    @staticmethod
    def _resolve_user_for_db(user, db_alias):
        if getattr(getattr(user, "_state", None), "db", None) == db_alias:
            return user
        try:
            return Usuario.objects.using(db_alias).get(pk=user.pk)
        except Usuario.DoesNotExist:
            pass
        try:
            return Usuario.objects.using(db_alias).get(username=user.username)
        except Usuario.DoesNotExist:
            pass
        mirrored_user, _ = Usuario.objects.using(db_alias).update_or_create(
            username=user.username,
            defaults={
                "password": user.password,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "nombres": getattr(user, "nombres", "") or "",
                "apellidos": getattr(user, "apellidos", "") or "",
                "telefono": getattr(user, "telefono", ""),
                "documento": getattr(user, "documento", ""),
                "rol": getattr(user, "rol", "conductor"),
                "tipo_documento": getattr(user, "tipo_documento", "CC"),
                "estado": getattr(user, "estado", "activo"),
                "foto_perfil": getattr(user, "foto_perfil", None),
                "sincronizado": True,
                "is_superuser": getattr(user, "is_superuser", False),
                "is_staff": getattr(user, "is_staff", False),
                "is_active": getattr(user, "is_active", True),
                "date_joined": getattr(user, "date_joined", None),
                "last_login": getattr(user, "last_login", None),
                "intentos_fallidos": getattr(user, "intentos_fallidos", 0),
                "bloqueado_hasta": getattr(user, "bloqueado_hasta", None),
                "nivel_bloqueo": getattr(user, "nivel_bloqueo", 0),
            },
        )
        return mirrored_user

    @property
    def asignacion_actual(self):
        from logistica.models import ConductorVehiculo
        if hasattr(self, "asignaciones_activas"):
            return self.asignaciones_activas[0] if self.asignaciones_activas else None
        return (
            ConductorVehiculo.objects.filter(conductor=self, fecha_fin__isnull=True)
            .select_related("vehiculo")
            .order_by("-fecha_asignacion")
            .first()
        )

    @property
    def vehiculo_actual(self):
        asignacion = self.asignacion_actual
        return asignacion.vehiculo if asignacion else None

    def asignar_vehiculo(self, vehiculo):
        from logistica.models import ConductorVehiculo
        if vehiculo is None:
            raise ValueError("El vehículo no puede ser None para la asignación.")
        if self.vehiculo_actual and self.vehiculo_actual.id_vehiculo == vehiculo.id_vehiculo:
            return self.vehiculo_actual
        ConductorVehiculo.objects.filter(conductor=self, fecha_fin__isnull=True).update(fecha_fin=now())
        nueva_asignacion = ConductorVehiculo.objects.create(conductor=self, vehiculo=vehiculo)
        return nueva_asignacion


class Notificacion(models.Model):
    TIPOS = [
        ("info", "Información"),
        ("success", "Éxito"),
        ("warning", "Advertencia"),
        ("danger", "Error"),
    ]
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="notificaciones")
    titulo = models.CharField(max_length=100, default="Nueva notificación")
    mensaje = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPOS, default="info")
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-fecha"]
        db_table = "notificacion"

    def __str__(self):
        return f"Notif {self.usuario}: {self.mensaje[:20]}..."


# Imports que requiere el nuevo save() lazy en el bloque condicional.
from django.db import IntegrityError, DatabaseError  # noqa: E402
