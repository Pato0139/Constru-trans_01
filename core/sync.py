import logging
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from core.utils import conexion_remota_disponible

logger = logging.getLogger(__name__)

Usuario = get_user_model()

def sync_usuarios_a_local():
    if not conexion_remota_disponible():
        logger.warning("No se pudo sincronizar a local: No hay conexión remota.")
        return

    try:
        usuarios_remotos = Usuario.objects.using('remota').all()

        for usuario in usuarios_remotos:
            Usuario.objects.using('default').update_or_create(
                username=usuario.username,
                defaults={
                    'password': usuario.password,
                    'nombres': usuario.nombres,
                    'apellidos': usuario.apellidos,
                    'email': usuario.email,
                    'telefono': usuario.telefono,
                    'documento': usuario.documento,
                    'rol': usuario.rol,
                }
            )
        logger.info("Usuarios sincronizados a local correctamente.")
    except Exception as e:
        logger.error(f"Error al sincronizar usuarios a local: {e}")


def sync_usuarios_a_remota():
    if not conexion_remota_disponible():
        logger.warning("No se pudo sincronizar a remota: No hay conexión remota.")
        return

    try:
        usuarios_locales_ns = Usuario.objects.using('default').filter(sincronizado=False)

        for usuario in usuarios_locales_ns:
            try:
                with transaction.atomic(using='remota'):
                    Usuario.objects.using('remota').update_or_create(
                        username=usuario.username,
                        defaults={
                            'password': usuario.password,
                            'nombres': usuario.nombres,
                            'apellidos': usuario.apellidos,
                            'email': usuario.email,
                            'telefono': usuario.telefono,
                            'documento': usuario.documento,
                            'rol': usuario.rol,
                        }
                    )
                    usuario.sincronizado = True
                    usuario.save(using='default')
            except IntegrityError:
                logger.warning(f"Conflicto al sincronizar usuario {usuario.username} a remota.")
        logger.info("Usuarios sincronizados a remota correctamente.")
    except Exception as e:
        logger.error(f"Error al sincronizar usuarios a remota: {e}")


def sync_all_usuarios():
    sync_usuarios_a_local()
    sync_usuarios_a_remota()
