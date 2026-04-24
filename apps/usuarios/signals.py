from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from .models import Usuario, Material, Stock

@receiver(post_save, sender=Material)
def create_material_stock(sender, instance, created, **kwargs):
    """Crea un registro de Stock cuando se crea un nuevo Material"""
    if created:
        Stock.objects.get_or_create(material=instance)

# -------------------------
# PROTECCIÓN DE SUPERUSUARIO GLOBAL
# -------------------------
PROTECTED_USERNAME = 'Edward_Fonseca'

@receiver(pre_save, sender=User)
def protect_global_admin_update(sender, instance, **kwargs):
    """Evita que se le quite el estado de superusuario al administrador global"""
    if instance.username == PROTECTED_USERNAME:
        # Forzar que siempre sea superusuario y staff
        instance.is_superuser = True
        instance.is_staff = True
        instance.is_active = True

@receiver(pre_save, sender=Usuario)
def protect_usuario_rol_update(sender, instance, **kwargs):
    """Evita que se le quite el rol de admin al administrador global en su perfil"""
    if instance.user and instance.user.username == PROTECTED_USERNAME:
        instance.rol = 'admin'
        instance.estado = 'activo'

@receiver(pre_delete, sender=User)
def protect_global_admin_delete(sender, instance, **kwargs):
    """Evita que el administrador global sea eliminado"""
    if instance.username == PROTECTED_USERNAME:
        raise PermissionDenied("No se puede eliminar al Administrador Global del sistema.")

@receiver(pre_delete, sender=Usuario)
def protect_usuario_perfil_delete(sender, instance, **kwargs):
    """Evita que el perfil de Usuario del administrador global sea eliminado"""
    if instance.user and instance.user.username == PROTECTED_USERNAME:
        raise PermissionDenied("No se puede eliminar el perfil del Administrador Global.")
