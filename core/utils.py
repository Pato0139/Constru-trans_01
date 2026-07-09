import os
import socket
from functools import lru_cache

from django.core.cache import cache
from django.db import connections
from django.db.utils import ConnectionDoesNotExist, OperationalError


@lru_cache(maxsize=1)
def conexion_remota_disponible_cached():
    try:
        if "remota" not in connections.databases:
            return False
        if not os.getenv("DATABASE_URL"):
            return False
        
        # First try a quick socket check if possible, but fall back to Django's ensure_connection
        # For now, just use Django's ensure_connection with the timeout we set in settings
        connections["remota"].ensure_connection()
        return True
    except (OperationalError, ConnectionDoesNotExist, Exception):
        return False


def conexion_remota_disponible():
    import time

    # Check cache first, and only refresh every 5 minutes (300s)
    cache_key = "core:conexion_remota_disponible"
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    
    # If not cached, check and set cache
    result = conexion_remota_disponible_cached()
    cache.set(cache_key, result, 300)  # Cache for 5 minutes
    return result


def get_cache_key(prefix, user_id, *args):
    key_parts = [str(prefix), str(user_id)]
    key_parts.extend(str(arg) for arg in args)
    return ":".join(key_parts)


def clear_user_cache(user_id):
    try:
        cache.delete_pattern(f"*:{user_id}:*")
    except Exception:
        cache.clear()
