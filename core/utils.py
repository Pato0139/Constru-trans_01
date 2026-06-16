import os
from functools import lru_cache

from django.core.cache import cache
from django.db import connections
from django.db.utils import ConnectionDoesNotExist, OperationalError


@lru_cache(maxsize=1)
def conexion_remota_disponible_cached():
    """
    Verifica si la conexión remota (Neon) está disponible.
    Usa lru_cache para no chequear constantemente, mejorando la velocidad!
    Cachea el resultado por 60 segundos (usamos un timestamp para invalidar).
    """
    try:
        if "remota" not in connections.databases:
            return False
        if not os.getenv("DATABASE_URL"):
            return False
        connections["remota"].ensure_connection()
        return True
    except (OperationalError, ConnectionDoesNotExist, Exception):
        return False


def conexion_remota_disponible():
    """
    Wrapper de la función cached, invalida el caché cada 60 segundos para
    no quedarse con un resultado obsoleto si la conexión se restablece.
    """
    import time

    # Si la caché está muy vieja, la invalidamos
    last_check = getattr(conexion_remota_disponible, "_last_check", 0)
    if time.time() - last_check > 60:  # 60 segundos
        conexion_remota_disponible_cached.cache_clear()
        conexion_remota_disponible._last_check = time.time()

    return conexion_remota_disponible_cached()


def get_cache_key(prefix, user_id, *args):
    """Crea una clave de caché única usando el prefijo y el ID del usuario."""
    key_parts = [str(prefix), str(user_id)]
    key_parts.extend(str(arg) for arg in args)
    return ":".join(key_parts)


def clear_user_cache(user_id):
    """Limpia todas las entradas de caché asociadas a un usuario."""
    # Obtener todas las claves que comienzan con el prefijo del usuario
    # Nota: LocMemCache no permite iterar todas las claves, pero para este caso
    # podemos usar patrones conocidos o limpiar todo el caché si es necesario
    try:
        cache.delete_pattern(f"*:{user_id}:*")
    except Exception:
        # Si el backend no soporta delete_pattern, limpiamos todo el caché
        cache.clear()
