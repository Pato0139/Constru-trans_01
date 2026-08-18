"""
Módulo de seguridad centralizado para Constru-trans.

- @role_required: control de acceso por rol con exención automática para superadmin.
- Bloqueo de IP por repetición de accesos no autorizados.
- Helpers para registrar SecurityEvent.
"""

import logging
from functools import wraps
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import OperationalError as DB_OperationalError
from django.db import ProgrammingError as DB_ProgrammingError
from django.db.utils import DatabaseError
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import BloqueoIP, SecurityEvent

logger = logging.getLogger(__name__)

# ============================================================
# Configuración (se puede sobreescribir via settings)
# ============================================================
MAX_WARNINGS_BEFORE_BLOCK = getattr(settings, "SECURITY_MAX_WARNINGS", 5)
BLOCK_DURATION_HOURS = getattr(settings, "SECURITY_BLOCK_HOURS", 24)
WARNING_WINDOW_MINUTES = getattr(settings, "SECURITY_WARNING_WINDOW", 60)
CACHE_PREFIX = "sec:"


# ============================================================
# Helpers genéricos
# ============================================================
def obtener_ip(request):
    """Obtiene la IP real del cliente (considerando proxies)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


def _cache_key_warnings(ip):
    return f"{CACHE_PREFIX}w:{ip}"


def _cache_key_blocked_flag(ip):
    return f"{CACHE_PREFIX}b:{ip}"


def contar_warnings_ventana(ip):
    cache_key = _cache_key_warnings(ip)
    data = cache.get(cache_key) or []
    now = timezone.now()
    recientes = [t for t in data if now - t <= timedelta(minutes=WARNING_WINDOW_MINUTES)]
    cache.set(cache_key, recientes, timeout=WARNING_WINDOW_MINUTES * 60 + 60)
    return len(recientes), recientes


def registrar_warning(ip):
    cache_key = _cache_key_warnings(ip)
    data = cache.get(cache_key) or []
    data.append(timezone.now())
    cache.set(cache_key, data, timeout=WARNING_WINDOW_MINUTES * 60 + 60)


def ip_esta_bloqueada(ip):
    cache_key = _cache_key_blocked_flag(ip)
    cached = cache.get(cache_key)
    if cached is True:
        return True
    if cached is False:
        return False

    try:
        bloqueo = BloqueoIP.obtener_bloqueo_vigente(ip)
    except (DB_ProgrammingError, DB_OperationalError, DatabaseError) as exc:
        logger.warning(
            "Tabla BloqueoIP no disponible (migración pendiente?). Omite check: %s", exc
        )
        return False
    cache.set(cache_key, bloqueo is not None, timeout=30)
    return bloqueo is not None


def bloquear_ip(ip, tipo="unauthorized_access", motivo="", duracion_horas=None, usuario=None):
    """Registra un bloqueo de IP y limpia caché."""
    if duracion_horas is None:
        duracion_horas = BLOCK_DURATION_HOURS

    expira = timezone.now() + timedelta(hours=duracion_horas)
    try:
        bloqueo = BloqueoIP.objects.create(
            ip=ip,
            tipo=tipo,
            motivo=motivo,
            expira_en=expira,
            activo=True,
            intentos_asociados=MAX_WARNINGS_BEFORE_BLOCK,
            bloqueado_por=usuario,
        )
    except Exception as exc:
        logger.warning("No se pudo crear BloqueoIP para %s: %s", ip, exc)
        bloqueo = None

    cache_key = _cache_key_blocked_flag(ip)
    cache.set(cache_key, True, timeout=duracion_horas * 3600)
    return bloqueo


def registrar_evento(request, tipo, gravedad="warning", detalles=None, advertencia_mostrada=False):
    """Registra un SecurityEvent a partir de un request Django."""
    try:
        ip = obtener_ip(request)
        user = getattr(request, "user", None)
        if user is not None and not user.is_authenticated:
            user = None
        username_str = user.username if user else request.POST.get("username", "")

        SecurityEvent.objects.create(
            tipo=tipo,
            gravedad=gravedad,
            ip=ip,
            usuario=user,
            username_str=username_str,
            path=request.path[:512],
            metodo_http=request.method,
            user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:512],
            referer=(request.META.get("HTTP_REFERER") or "")[:512],
            detalles=detalles or {},
            advertencia_mostrada=advertencia_mostrada,
        )
    except Exception as exc:
        logger.error("Fallo al registrar SecurityEvent: %s", exc)


def _respuesta_no_autorizada(request, detalles=None, need_block=False):
    """Devuelve respuesta HTTP apropiada (HTML o JSON) tras acceso no autorizado."""
    ip = obtener_ip(request)
    num_warnings, _ = contar_warnings_ventana(ip)

    warnings_left = max(0, MAX_WARNINGS_BEFORE_BLOCK - num_warnings)
    will_block = num_warnings + 1 >= MAX_WARNINGS_BEFORE_BLOCK
    remaining_time = WARNING_WINDOW_MINUTES

    data_headers = {
        "X-Security-Warnings": str(num_warnings + 1),
        "X-Security-Warnings-Limit": str(MAX_WARNINGS_BEFORE_BLOCK),
        "X-Security-Warnings-Remaining": str(warnings_left - 1 if warnings_left > 0 else 0),
        "X-Security-Will-Block": "1" if will_block else "0",
    }

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or request.accepts("application/json")

    if will_block:
        bloquear_ip(
            ip,
            tipo="unauthorized_access",
            motivo=f"Accesos no autorizados repetidos en ventana de {WARNING_WINDOW_MINUTES} min.",
        )
        data_headers["X-IP-Blocked"] = "1"
        data_headers["X-IP-Blocked-Hours"] = str(BLOCK_DURATION_HOURS)

    if is_ajax:
        payload = {
            "error": "No tienes permisos para acceder a este recurso.",
            "security": {
                "warnings_count": num_warnings + 1,
                "warnings_limit": MAX_WARNINGS_BEFORE_BLOCK,
                "warnings_remaining": max(0, warnings_left - 1),
                "window_minutes": remaining_time,
                "blocked": will_block,
                "block_hours": BLOCK_DURATION_HOURS if will_block else 0,
                "message": (
                    "⚠️ ACCESO NO AUTORIZADO. Esta acción queda registrada. "
                    + (
                        f"Si realizas {warnings_left} intento(s) más en los próximos {remaining_time} minutos, "
                        f"tu IP quedará BLOQUEADA por {BLOCK_DURATION_HOURS} horas."
                        if not will_block
                        else f"Tu IP ha sido bloqueada {BLOCK_DURATION_HOURS} horas por intentos repetidos. Contacta a soporte."
                    )
                ),
            },
        }
        if detalles:
            payload["details"] = detalles
        response = JsonResponse(payload, status=403)
    else:
        context = {
            "security_warnings_count": num_warnings + 1,
            "security_warnings_limit": MAX_WARNINGS_BEFORE_BLOCK,
            "security_warnings_remaining": max(0, warnings_left - 1),
            "security_window_minutes": remaining_time,
            "security_blocked": will_block,
            "security_block_hours": BLOCK_DURATION_HOURS,
            "security_detalles": detalles,
        }
        response = render(request, "errors/403_security.html", context=context, status=403)

    for k, v in data_headers.items():
        response[k] = v
    return response


# ============================================================
# Decorador central: role_required
# ============================================================
def role_required(roles, *, login=True):
    """
    Decorador para exigir que el usuario autenticado tenga uno de los roles indicados.

    - Si el usuario es SUPERADMIN (request.user.es_superuser o is_superuser): exención TOTAL.
      Puede entrar a TODO.
    - Si el rol del usuario NO está en la lista:
        - Registra SecurityEvent
        - Suma warning a la IP
        - Devuelve 403 con alerta (HTML o JSON según request)
        - Si alcanzó MAX_WARNINGS_BEFORE_BLOCK en ventana de tiempo: BLOQUEA LA IP
    """

    allowed = set(roles)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            # 1. Login obligatorio a menos que se indique lo contrario
            if login and not getattr(request, "user", None):
                return redirect("usuarios:login")
            if login and not request.user.is_authenticated:
                return redirect("usuarios:login")

            user = request.user

            # 2. SUPERADMIN: puede acceder a TODO sin restricciones
            if getattr(user, "is_superuser", False) or getattr(user, "es_superadmin", False):
                return view_func(request, *args, **kwargs)

            # 3. Rol correcto → pasar
            user_role = getattr(user, "rol", None)
            if user_role in allowed:
                return view_func(request, *args, **kwargs)

            # 4. Fallo: rol no permitido
            ip = obtener_ip(request)
            registrar_warning(ip)
            registrar_evento(
                request,
                "role_violation",
                gravedad="high",
                detalles={
                    "rol_requerido": roles,
                    "rol_usuario": user_role,
                    "usuario_id": user.pk,
                },
            )

            logger.warning(
                "[SEC] role_violation user=%s (%s) path=%s role_needed=%s warnings=%s",
                user.username,
                user_role,
                request.path,
                roles,
                contar_warnings_ventana(ip)[0],
            )

            return _respuesta_no_autorizada(
                request,
                detalles={
                    "rol_requerido": sorted(allowed),
                    "rol_usuario": user_role,
                },
            )

        if login:
            return login_required(_wrapped)
        return _wrapped

    return decorator


# ============================================================
# Decorador legacy: admin_required (bypass superadmin)
# ============================================================
def admin_required(view_func):
    """
    Alias legacy para @role_required(["admin"]) — compatible con el código existente.
    El superadmin pasa siempre.
    """
    return role_required(["admin"])(view_func)
