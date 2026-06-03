import logging
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from core.utils import conexion_remota_disponible

logger = logging.getLogger(__name__)

Usuario = get_user_model()

def sync_usuarios_a_local():
    """
    Sincroniza los usuarios de la base de datos remota hacia la local (default).
    Se usa para poder iniciar sesión offline.
    """
    if not conexion_remota_disponible():
        logger.warning("No se pudo sincronizar a local: No hay conexión remota.")
        return

    try:
        usuarios_remotos = Usuario.objects.using('remota').all()
        
        for usuario in usuarios_remotos:
            # Sincronizamos a local, basándonos en el username que es único
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
                    'tipo_documento': usuario.tipo_documento,
                    'estado': usuario.estado,
                    'foto_perfil': usuario.foto_perfil,
                    'sincronizado': True,
                    'is_superuser': usuario.is_superuser,
                    'is_staff': usuario.is_staff,
                    'is_active': usuario.is_active,
                    'date_joined': usuario.date_joined,
                    'last_login': usuario.last_login,
                }
            )
        logger.info(f"Se sincronizaron {usuarios_remotos.count()} usuarios a la BD local.")
    except Exception as e:
        logger.error(f"Error sincronizando usuarios a local: {str(e)}")


def sync_usuarios_a_remoto():
    """
    Sincroniza los usuarios locales nuevos (sincronizado=False) a la BD remota.
    """
    if not conexion_remota_disponible():
        logger.warning("No se pudo sincronizar a remoto: No hay conexión remota.")
        return

    try:
        usuarios_no_sincronizados = Usuario.objects.using('default').filter(sincronizado=False)
        
        for usuario in usuarios_no_sincronizados:
            try:
                # Sincronizamos a remota, basándonos en el username
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
                        'tipo_documento': usuario.tipo_documento,
                        'estado': usuario.estado,
                        'foto_perfil': usuario.foto_perfil,
                        'sincronizado': True,
                        'is_superuser': usuario.is_superuser,
                        'is_staff': usuario.is_staff,
                        'is_active': usuario.is_active,
                        'date_joined': usuario.date_joined,
                        'last_login': usuario.last_login,
                    }
                )
                # Actualizamos en local para no volver a sincronizarlo
                usuario.sincronizado = True
                usuario.save(using='default')
            except IntegrityError as e:
                logger.error(f"Error de integridad al sincronizar usuario {usuario.username}: {str(e)}")
            except Exception as e:
                logger.error(f"Error sincronizando usuario {usuario.username} a remoto: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error general en sync_usuarios_a_remoto: {str(e)}")


def sync_all_usuarios():
    """Ejecuta la sincronización bidireccional completa."""
    if conexion_remota_disponible():
        sync_usuarios_a_remoto()
        sync_usuarios_a_local()
