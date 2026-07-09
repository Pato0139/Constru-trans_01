"""
Preferencia de base de datos (local / remota) por sesión de usuario.
El middleware establece el valor en thread-local para que el router lo use.     
"""
import threading

PREF_LOCAL = 'local'
PREF_REMOTA = 'remota'
PREF_AUTO = 'auto'

VALID_PREFS = frozenset({PREF_LOCAL, PREF_REMOTA, PREF_AUTO})

_local = threading.local()


def set_db_preference(preference: str) -> None:
    _local.preference = preference if preference in VALID_PREFS else PREF_AUTO  


def get_db_preference() -> str:
    return getattr(_local, 'preference', PREF_AUTO)


def clear_db_preference() -> None:
    if hasattr(_local, 'preference'):
        del _local.preference


def debe_usar_bd_remota() -> bool:
    from django.conf import settings
    from core.utils import conexion_remota_disponible

    if 'remota' not in settings.DATABASES:
        return False

    preference = get_db_preference()

    if preference == PREF_REMOTA:
        return conexion_remota_disponible()
    elif preference == PREF_LOCAL:
        return False
    else:  # PREF_AUTO
        return conexion_remota_disponible()


def invalidate_connection_cache() -> None:
    from core.utils import conexion_remota_disponible_cached
    conexion_remota_disponible_cached.cache_clear()
