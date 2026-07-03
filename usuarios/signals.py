from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import MaterialConstruccion, HistorialPrecioMaterial


@receiver(pre_save, sender=MaterialConstruccion)
def registrar_cambio_precio(sender, instance, **kwargs):
    """
    Registra el cambio de precio de un material en el historial.
    """
    if instance.pk:
        try:
            material_anterior = MaterialConstruccion.objects.get(pk=instance.pk)
            if material_anterior.precio_referencia != instance.precio_referencia:
                # El precio ha cambiado, registramos en el historial
                HistorialPrecioMaterial.objects.create(
                    material=instance,
                    precio_anterior=material_anterior.precio_referencia,
                    precio_nuevo=instance.precio_referencia,
                    observaciones=f"Cambio de precio desde {material_anterior.precio_referencia} hasta {instance.precio_referencia}"
                )
        except MaterialConstruccion.DoesNotExist:
            pass


import os
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_delete, pre_save
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

