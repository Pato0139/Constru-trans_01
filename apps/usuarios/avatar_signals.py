"""
Señal automática para asignar avatar estilo Google (inicial + color)
a cada nuevo usuario registrado sin foto de perfil.
"""

import sys

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.usuarios.avatars import asegurar_avatar_usuario
from apps.usuarios.models import Usuario


@receiver(post_save, sender=Usuario, dispatch_uid="usuarios_avatar_google_auto")
def asignar_avatar_inicial_usuario(sender, instance, created, using=None, **kwargs):
    if not created:
        return
    if "test" in sys.argv or "pytest" in sys.modules:
        return
    if getattr(instance, "foto_perfil", None) and getattr(instance.foto_perfil, "name", ""):
        return

    db_alias = using or getattr(instance._state, "db", None) or "default"
    asegurar_avatar_usuario(instance, using=db_alias, force=False)
