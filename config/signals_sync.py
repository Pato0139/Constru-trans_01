"""
Señales de replicación bidireccional en tiempo real:
  - Remota (Neon) -> Local (SQLite): mantiene la base offline siempre al día.
  - Local/Default (SQLite) -> Remota (Neon): asegura que notificaciones, usuarios
    y pedidos creados/editados localmente se publiquen de inmediato en Neon para otros PCs.
"""

import sys

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from config.sync_local import (
    MODELOS_SINCRONIZABLES,
    eliminar_instancia_en_local,
    esta_sincronizando,
    replicar_instancia_a_local,
    replicar_instancia_a_remota,
)


def _debe_replicar_a_local(sender, using) -> bool:
    if "test" in sys.argv or "pytest" in sys.modules:
        return False
    if esta_sincronizando():
        return False
    if using != "remota":
        return False
    if "local" not in settings.DATABASES:
        return False
    return getattr(sender._meta, "label", None) in MODELOS_SINCRONIZABLES


def _debe_replicar_a_remota(sender, using) -> bool:
    if "test" in sys.argv or "pytest" in sys.modules:
        return False
    if esta_sincronizando():
        return False
    if getattr(settings, "OFFLINE_MODE", False):
        return False
    if using not in {"default", "local"}:
        return False
    if "remota" not in settings.DATABASES:
        return False
    return getattr(sender._meta, "label", None) in MODELOS_SINCRONIZABLES


@receiver(post_save, dispatch_uid="core_replicar_remota_a_local_save")
def replicar_guardado_a_local(sender, instance, using=None, **kwargs):
    db_used = using or getattr(instance._state, "db", None)
    if _debe_replicar_a_local(sender, db_used):
        replicar_instancia_a_local(instance)
    elif _debe_replicar_a_remota(sender, db_used):
        replicar_instancia_a_remota(instance)


@receiver(post_delete, dispatch_uid="core_replicar_remota_a_local_delete")
def replicar_borrado_a_local(sender, instance, using=None, **kwargs):
    db_used = using or getattr(instance._state, "db", None)
    if _debe_replicar_a_local(sender, db_used):
        eliminar_instancia_en_local(instance)
