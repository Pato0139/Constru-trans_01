from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


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
    direccion_principal = models.CharField(max_length=200, default="Por definir")
    tipo_cliente = models.CharField(max_length=20, choices=TIPOS_CLIENTE, default="persona")
    nombre_empresa = models.CharField(max_length=200, default="", blank=True)
    nit = models.CharField(max_length=20, default="", blank=True)
    contacto_alternativo = models.CharField(max_length=100, default="", blank=True)
    observaciones = models.TextField(default="", blank=True)

    # NO cambien nada aca
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cliente"

    def __str__(self):
        return self.usuario.nombres


@receiver(post_save, sender="usuarios.Usuario")
def crear_perfil_cliente(sender, instance, created, **kwargs):
    """Auto-crea perfil Cliente si el usuario tiene rol 'cliente'."""
    if created and instance.rol == "cliente":
        using = kwargs.get("using") or instance._state.db or "default"
        Cliente.objects.using(using).get_or_create(
            usuario=instance,
            defaults={"direccion_principal": "Por definir"},
        )
