import logging
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from core.utils import conexion_remota_disponible

logger = logging.getLogger(__name__)

Usuario = get_user_model()

def _campos_usuario_defaults(usuario):
    """Devuelve el diccionario completo de campos para sincronizar un Usuario entre BD."""
    return {
        'password': usuario.password,
        'nombres': usuario.nombres,
        'apellidos': usuario.apellidos,
        'email': usuario.email,
        'telefono': usuario.telefono,
        'documento': usuario.documento,
        'tipo_documento': getattr(usuario, 'tipo_documento', 'CC'),
        'rol': usuario.rol,
        'estado': getattr(usuario, 'estado', 'activo'),
        'sincronizado': getattr(usuario, 'sincronizado', False),
        'is_active': getattr(usuario, 'is_active', True),
        'is_staff': getattr(usuario, 'is_staff', False),
        'is_superuser': getattr(usuario, 'is_superuser', False),
        'first_name': getattr(usuario, 'first_name', '') or '',
        'last_name': getattr(usuario, 'last_name', '') or '',
        'intentos_fallidos': getattr(usuario, 'intentos_fallidos', 0),
        'bloqueado_hasta': getattr(usuario, 'bloqueado_hasta', None),
        'nivel_bloqueo': getattr(usuario, 'nivel_bloqueo', 0),
        'date_joined': getattr(usuario, 'date_joined', None),
        'last_login': getattr(usuario, 'last_login', None),
    }


def sync_usuarios_a_local():
    if not conexion_remota_disponible():
        logger.warning("No se pudo sincronizar a local: No hay conexión remota.")
        return

    try:
        usuarios_remotos = Usuario.objects.using('remota').all()

        for usuario in usuarios_remotos:
            defaults = _campos_usuario_defaults(usuario)
            defaults['sincronizado'] = True
            Usuario.objects.using('default').update_or_create(
                username=usuario.username,
                defaults=defaults
            )
        logger.info("Usuarios sincronizados a local correctamente.")
    except Exception as e:
        logger.error(f"Error al sincronizar usuarios a local: {e}", exc_info=True)


def sync_usuarios_a_remota():
    if not conexion_remota_disponible():
        logger.warning("No se pudo sincronizar a remota: No hay conexión remota.")
        return

    try:
        usuarios_locales_ns = Usuario.objects.using('default').filter(sincronizado=False)

        for usuario in usuarios_locales_ns:
            try:
                with transaction.atomic(using='remota'):
                    defaults = _campos_usuario_defaults(usuario)
                    Usuario.objects.using('remota').update_or_create(
                        username=usuario.username,
                        defaults=defaults
                    )
                    usuario.sincronizado = True
                    usuario.save(using='default')
            except IntegrityError:
                logger.warning(f"Conflicto al sincronizar usuario {usuario.username} a remota.")
        logger.info("Usuarios sincronizados a remota correctamente.")
    except Exception as e:
        logger.error(f"Error al sincronizar usuarios a remota: {e}", exc_info=True)


def sync_all_usuarios():
    sync_usuarios_a_local()
    sync_usuarios_a_remota()
