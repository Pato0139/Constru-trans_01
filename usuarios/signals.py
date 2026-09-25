import os
from django.core.exceptions import PermissionDenied
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from .models import Usuario


def _normalizar_lista_env(nombre_variable):
    raw = os.getenv(nombre_variable, "")
    return {x.strip().lower() for x in raw.split(",") if x.strip()}


PROTECTED_ADMIN_USERNAMES = _normalizar_lista_env("PROTECTED_ADMIN_USERNAMES")
PROTECTED_ADMIN_EMAILS = _normalizar_lista_env("PROTECTED_ADMIN_EMAILS")


def es_admin_global_protegido(usuario: Usuario) -> bool:
    if not usuario:
        return False

    username = (usuario.username or "").strip().lower()
    email = (usuario.email or "").strip().lower()

    return (
        usuario.is_superuser
        and (
            username in PROTECTED_ADMIN_USERNAMES
            or email in PROTECTED_ADMIN_EMAILS
        )
    )


@receiver(pre_delete, sender=Usuario)
def impedir_borrado_admin_global(sender, instance, **kwargs):
    if es_admin_global_protegido(instance):
        raise PermissionDenied("❌ No se puede eliminar el admin global protegido.")


@receiver(pre_save, sender=Usuario)
def impedir_desactivar_admin_global(sender, instance, **kwargs):
    if not instance.pk:
        return

    anterior = Usuario.objects.filter(pk=instance.pk).first()
    if not anterior:
        return

    if es_admin_global_protegido(anterior):
        if not instance.is_superuser:
            raise PermissionDenied("❌ No se puede quitar el superusuario al admin global.")
        if not instance.is_active:
            raise PermissionDenied("❌ No se puede desactivar el admin global.")
        if instance.rol != anterior.rol:
            raise PermissionDenied("❌ No se puede cambiar el rol del admin global.")


@receiver(post_save, sender=Usuario)
def crear_perfil_conductor(sender, instance, created, using=None, **kwargs):
    if created and instance.rol == "conductor":
        from .models import Conductor

        Conductor.ensure_for_user(instance, using=using or instance._state.db or "default")
