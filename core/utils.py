import logging
import os
import socket
from functools import lru_cache

from django.core.cache import cache
from django.db import connections
from django.db.utils import ConnectionDoesNotExist, OperationalError

logger = logging.getLogger(__name__)

_REMOTA_NEGATIVA_TTL = 15
_REMOTA_POSITIVA_TTL = 300


def _socket_check_rapido(host, port, timeout=2.0):
    """Prueba TCP rápida sin tocar psycopg2. Si no llega en 2s, asumimos offline."""
    if not (host and port):
        return None  # no podemos validar por socket; que lo decida ensure_connection
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
    except Exception:
        return None


def _host_port_from_database_url():
    url = os.getenv("DATABASE_URL", "") or ""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 5432
        return host, port
    except Exception:
        return None, None


@lru_cache(maxsize=1)
def conexion_remota_disponible_cached():
    if "remota" not in connections.databases:
        return False
    if not os.getenv("DATABASE_URL"):
        return False

    host, port = _host_port_from_database_url()
    rapido = _socket_check_rapido(host, port, timeout=2.0)
    if rapido is False:
        return False

    try:
        connections["remota"].ensure_connection()
        return True
    except (OperationalError, ConnectionDoesNotExist, Exception):
        return False


def conexion_remota_disponible():
    cache_key = "core:conexion_remota_disponible"
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    result = conexion_remota_disponible_cached()
    ttl = _REMOTA_POSITIVA_TTL if result else _REMOTA_NEGATIVA_TTL
    cache.set(cache_key, result, ttl)
    return result


def get_cache_key(prefix, user_id, *args):
    key_parts = [str(prefix), str(user_id)]
    key_parts.extend(str(arg) for arg in args)
    return ":".join(key_parts)


def _registry_key(user_id):
    return f"core:user_cache_keys:{user_id}"


def set_user_cache(prefix, user_id, value, *args, timeout=None):
    """Guarda un valor en cache usando get_cache_key y lo registra
    para poder borrarlo puntualmente después (sin cache.clear() global).
    Usar esta función en vez de cache.set(get_cache_key(...), value)
    para todo lo que se guarde ligado a un usuario.
    """
    key = get_cache_key(prefix, user_id, *args)
    cache.set(key, value, timeout)

    registry_key = _registry_key(user_id)
    keys = cache.get(registry_key) or set()
    keys.add(key)
    cache.set(registry_key, keys, None)
    return key


def clear_user_cache(user_id):
    """Limpia solo la cache de este usuario, sin afectar a los demás."""
    if hasattr(cache, "delete_pattern"):
        try:
            cache.delete_pattern(f"*:{user_id}:*")
            return
        except Exception:
            logger.warning("delete_pattern falló para usuario %s", user_id, exc_info=True)

    registry_key = _registry_key(user_id)
    keys = cache.get(registry_key)
    if keys:
        try:
            cache.delete_many(list(keys))
        except OSError:
            logger.warning("No se pudo borrar cache (FileBasedCache) para usuario %s", user_id, exc_info=True)
        cache.delete(registry_key)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def registrar_actividad(request, accion, modulo, elemento_id=None, descripcion=""):
    from core.models import Historial

    usuario = request.user if request and request.user.is_authenticated else None
    ip_address = get_client_ip(request) if request else None

    datos = {
        "usuario": usuario,
        "accion": accion,
        "modulo": modulo,
        "elemento_id": str(elemento_id) if elemento_id else None,
        "descripcion": descripcion,
        "ip_address": ip_address,
    }

    try:
        Historial.objects.create(**datos)
    except Exception:
        from django.db import IntegrityError
        logger.warning("No se pudo asociar el usuario al historial; se guardará sin usuario.")
        datos["usuario"] = None
        Historial.objects.create(**datos)