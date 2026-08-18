from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from usuarios.models import Usuario


# =====================================================================
# CLIENTE
# =====================================================================
class Cliente(models.Model):
    TIPOS_CLIENTE = [
        ("persona", "Persona Natural"),
        ("empresa", "Empresa"),
        ("gobierno", "Entidad Gubernamental"),
    ]

    usuario = models.OneToOneField(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="perfil_cliente",
    )

    # Campos del MER (ClienteVIP)
    nombre_empresa = models.CharField(max_length=200, default="", blank=True)
    direccion_principal = models.CharField(max_length=200, default="Por definir")
    es_vip = models.BooleanField(default=False)
    fecha_vip = models.DateField(null=True, blank=True)
    gasto_acumulado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Gasto acumulado",
    )

    # Campos legacy / adicionales
    direccion = models.CharField(max_length=200, default="Por definir")
    tipo_cliente = models.CharField(max_length=20, choices=TIPOS_CLIENTE, default="persona")
    nit = models.CharField(max_length=20, default="", blank=True)
    contacto_alternativo = models.CharField(max_length=100, default="", blank=True)
    observaciones = models.TextField(default="", blank=True)

    # NO cambien nada aca
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cliente_vip"
        verbose_name = "Cliente VIP"
        verbose_name_plural = "Clientes VIP"

    def __str__(self):
        return self.usuario.nombres

    @classmethod
    def ensure_for_user(cls, user, using=None, defaults=None):
        """Crea o devuelve el perfil de cliente para un usuario persistido."""
        if user is None:
            raise ValueError("Se requiere un usuario válido para crear el perfil de cliente.")

        if not getattr(user, "pk", None):
            raise ValueError(
                "El usuario debe existir en base de datos antes de crear el perfil de cliente."
            )

        db_alias = using or getattr(getattr(user, "_state", None), "db", None) or "default"
        user_for_profile = cls._resolve_user_for_db(user, db_alias)

        if user_for_profile is None:
            raise ValueError("No fue posible resolver un usuario válido para el perfil de cliente.")

        profile_defaults = {
            "direccion": "Por definir",
            "direccion_principal": "Por definir",
            "gasto_acumulado": 0,
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
                "rol": getattr(user, "rol", "cliente"),
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

    def save(self, *args, **kwargs):
        if not self.direccion_principal and self.direccion:
            self.direccion_principal = self.direccion
        super().save(*args, **kwargs)


# Alias del MER: Cliente → ClienteVIP
ClienteVIP = Cliente


@receiver(post_save, sender="usuarios.Usuario")
def crear_perfil_cliente(sender, instance, created, **kwargs):
    """Auto-crea perfil Cliente si el usuario tiene rol 'cliente'."""
    if created and instance.rol == "cliente":
        using = kwargs.get("using") or instance._state.db or "default"
        Cliente.ensure_for_user(
            instance,
            using=using,
            defaults={
                "direccion": "Por definir",
                "direccion_principal": "Por definir",
                "gasto_acumulado": 0,
            },
        )