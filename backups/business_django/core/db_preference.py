"""
Preferencia de base de datos (local / remota) por sesión de usuario.
El middleware establece el valor en thread-local para que el router lo use.
"""

import threading

PREF_LOCAL = "local"
PREF_REMOTA = "remota"
PREF_AUTO = "auto"

VALID_PREFS = frozenset({PREF_LOCAL, PREF_REMOTA, PREF_AUTO})

_local = threading.local()


def set_db_preference(preference: str) -> None:
    _local.preference = preference if preference in VALID_PREFS else PREF_AUTO


def get_db_preference() -> str:
    return getattr(_local, "preference", PREF_AUTO)


def clear_db_preference() -> None:
    if hasattr(_local, "preference"):
        del _local.preference


def debe_usar_bd_remota() -> bool:
    """
    Decide si el router debe enviar APPS_NUBE a la BD remota.
    Ahora, por defecto usará el modo remoto si está disponible.
    """
    from core.utils import conexion_remota_disponible

    pref = get_db_preference()
    if pref == PREF_LOCAL:
        return False
    # Siempre intentar usar remoto si está disponible
    return conexion_remota_disponible()


def invalidate_connection_cache() -> None:
    from core.utils import conexion_remota_disponible, conexion_remota_disponible_cached

    conexion_remota_disponible_cached.cache_clear()
    if hasattr(conexion_remota_disponible, "_last_check"):
        del conexion_remota_disponible._last_check
