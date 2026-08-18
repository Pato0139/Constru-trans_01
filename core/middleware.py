import logging

from django.http import HttpResponseForbidden
from django.shortcuts import render

from core.db_preference import PREF_AUTO, PREF_REMOTA, clear_db_preference, set_db_preference
from core.security import (
    BloqueoIP,
    SecurityEvent,
    _respuesta_no_autorizada,
    contar_warnings_ventana,
    ip_esta_bloqueada,
    obtener_ip,
    registrar_evento,
    registrar_warning,
)
from core.utils import conexion_remota_disponible

logger = logging.getLogger(__name__)


BLOCKED_PATH_WHITELIST = (
    "/licensing/",
    "/static/",
    "/media/",
    "/__reload__/",
    "/usuarios/login/",
    "/usuarios/logout/",
    "/usuarios/registro/",
    "/usuarios/recuperar/",
    "/usuarios/bd/cambiar/",
    "/admin/",
)


def _namespace_from_path(path):
    """Determina el app_namespace / nombre de módulo a partir del path de URL."""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return "inicio"
    first = parts[0]
    if first in {"usuarios", "clientes", "inventario", "compras", "ordenes",
                  "facturacion", "pagos", "reportes", "historial", "transporte",
                  "ia", "ayuda", "pedidos", "gestion_pedidos", "licensing", "inicio"}:
        return first
    return None


_NAMESPACE_ROLES = {
    "inventario": {"admin"},
    "compras": {"admin"},
    "transporte": {"admin"},
    "reportes": {"admin"},
    "historial": {"admin"},
    "gestion_pedidos": {"admin"},
    "pedidos": {"admin"},
    "inicio": {"admin", "cliente", "conductor", "empleado"},
    "ia": {"admin", "cliente", "conductor", "empleado"},
    "ayuda": {"admin", "cliente", "conductor", "empleado"},
    "licensing": {"admin", "cliente", "conductor", "empleado"},
}


_USUARIOS_URLNAMES_ROLES = {
    "lista_usuarios": {"admin"},
    "crear_usuario": {"admin"},
    "eliminar_usuario": {"admin"},
    "toggle_estado_usuario": {"admin"},
    "editar_usuario": {"admin"},
    "lista_conductores": {"admin"},
    "asignar_vehiculo_conductor": {"admin"},
    "panel_conductor": {"conductor"},
    "pedidos_conductor": {"conductor"},
    "mis_entregas": {"conductor"},
}


_ORDENES_URLNAMES_ROLES = {
    "calcular_total": {"admin"},
    "eliminar_detalle": {"admin"},
    "agregar_materiales": {"admin"},
    "lista_pedidos_admin": {"admin"},
    "lista_entregas_admin": {"admin"},
    "crear_orden": {"admin"},
    "detalle_orden": {"admin"},
    "crear_pedido_admin": {"admin"},
    "asignar_entrega": {"admin"},
}


_URLNAMES_BY_ROLE_EXTRA = {
    "facturacion": {
        "lista_facturas": {"admin"},
        "anular_factura": {"admin"},
        "editar_factura_monto": {"admin"},
        "mis_facturas": {"cliente"},
    },
    "pagos": {
        "gestion_pagos": {"admin"},
        "lista_pagos": {"admin"},
    },
    "clientes": {
        "panel_cliente": {"cliente"},
        "mis_pedidos": {"cliente"},
        "perfil_cliente": {"cliente"},
        "seguimiento_pedidos": {"cliente"},
        "historial_pedidos": {"cliente"},
        "crear_pedido": {"cliente"},
        "editar_pedido": {"cliente", "admin"},
        "cancelar_pedido": {"cliente", "admin"},
        "mis_pagos": {"cliente"},
        "lista": {"admin"},
        "detalle": {"admin"},
        "form": {"admin"},
    },
}


class RoleNamespaceMiddleware:
    """
    Middleware de SEGURIDAD EN PROFUNDA — Red de seguridad a nivel de URL namespace
    y url_name.

    Se ejecuta ANTES de cualquier vista y valida:
      1. Whitelist de paths públicos (login, static, etc.) → pasa
      2. Superadmin o Administrador Global → pasa TODO
      3. Namespace general (primer nivel /xxx/) en _NAMESPACE_ROLES
      4. url_name granular por app
      5. Si no se permite el rol → dispara cadena de seguridad:
           · Registrar warning en ventana de tiempo
           · Registrar SecurityEvent con detalles
           · Si se supera SECURITY_MAX_WARNINGS → BLOQUEO POR IP
           · Devuelve respuesta 403 de seguridad con alerta visual
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info or "/"

        # Si la protección falla por cualquier causa (BD, imports, etc.)
        # NO romper el sitio; caer al comportamiento normal y registrar warning.
        try:
            if any(path.startswith(p) for p in BLOCKED_PATH_WHITELIST):
                return self.get_response(request)

            user = getattr(request, "user", None)
            if user is None or not getattr(user, "is_authenticated", False):
                return self.get_response(request)

            is_super = getattr(user, "is_superuser", False) or getattr(user, "es_superadmin", False)
            if is_super:
                return self.get_response(request)

            user_role = getattr(user, "rol", None)
            ip = obtener_ip(request)
            namespace = _namespace_from_path(path)

            allowed_roles_ns = _NAMESPACE_ROLES.get(namespace)
            if allowed_roles_ns is not None and user_role not in allowed_roles_ns:
                return self._violacion(
                    request, ip, user_role,
                    detalle={
                        "causa": "namespace_restringido",
                        "namespace": namespace,
                        "roles_permitidos": sorted(allowed_roles_ns),
                        "path": path,
                    },
                )

            try:
                from django.urls import resolve
                match = resolve(path)
                url_name = match.url_name
                app_name = match.app_name or match.namespace or ""

                perms_extra = _URLNAMES_BY_ROLE_EXTRA.get(app_name, {})
                allowed_roles_url = perms_extra.get(url_name)
                if not allowed_roles_url and app_name == "usuarios":
                    allowed_roles_url = _USUARIOS_URLNAMES_ROLES.get(url_name)
                if not allowed_roles_url and app_name == "ordenes":
                    allowed_roles_url = _ORDENES_URLNAMES_ROLES.get(url_name)

                if allowed_roles_url and user_role not in allowed_roles_url:
                    return self._violacion(
                        request, ip, user_role,
                        detalle={
                            "causa": "url_restringida",
                            "app_name": app_name,
                            "url_name": url_name,
                            "roles_permitidos": sorted(allowed_roles_url),
                            "path": path,
                        },
                    )
            except Exception:
                pass
        except Exception as _exc:
            logger.error(
                "RoleNamespaceMiddleware falló (no aplicará filtros) — path=%s error=%s",
                path,
                _exc,
                exc_info=True,
            )
        return self.get_response(request)

    @staticmethod
    def _violacion(request, ip, user_role, detalle):
        try:
            registrar_warning(ip)
        except Exception:
            pass
        try:
            registrar_evento(
                request,
                "role_violation",
                gravedad="high",
                detalles=detalle,
            )
        except Exception:
            pass
        try:
            logger.warning(
                "[SEC-MW] role_violation ip=%s user=%s (%s) path=%s detalle=%s warnings=%s",
                ip,
                getattr(request.user, "username", "?"),
                user_role,
                request.path,
                detalle,
                contar_warnings_ventana(ip)[0],
            )
        except Exception:
            pass
        try:
            return _respuesta_no_autorizada(
                request,
                detalles={
                    "rol_usuario": user_role,
                    **detalle,
                },
            )
        except Exception as exc:
            logger.error("_respuesta_no_autorizada no renderizó (¿template no encontrado?): %s", exc)
            return HttpResponseForbidden(
                "Acceso no autorizado. Intento registrado en el sistema de seguridad."
            )


class DatabasePreferenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        pref = request.COOKIES.get("bd_preferida")
        if not pref:
            pref = request.session.get("bd_preferida", PREF_AUTO)

        if pref == PREF_AUTO and conexion_remota_disponible():
            pref = PREF_REMOTA

        set_db_preference(pref)
        try:
            return self.get_response(request)
        finally:
            clear_db_preference()


class SecurityMiddleware:
    """
    Middleware que:
    1. Detecta si la IP está bloqueada y le muestra página de bloqueo en TODO el sitio
       (excepto whitelist de licensing/static/usuarios/login).
    2. Cuenta warnings pendientes y expone la info al template (para alertas front).
    3. Inyecta headers de alerta para que el frontend muestre toast.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info or "/"

        skip_check = any(path.startswith(p) for p in BLOCKED_PATH_WHITELIST)

        ip = obtener_ip(request)
        if not skip_check:
            try:
                esta_bloq = ip_esta_bloqueada(ip)
            except Exception as _exc:
                logger.warning("SecurityMiddleware no pudo verificar bloqueo IP: %s", _exc)
                esta_bloq = False
            if esta_bloq:
                bloqueo = BloqueoIP.obtener_bloqueo_vigente(ip)
                horas = None
                if bloqueo and bloqueo.expira_en:
                    from django.utils import timezone

                    delta = bloqueo.expira_en - timezone.now()
                    horas = max(0, round(delta.total_seconds() / 3600))
                    if horas <= 0:
                        horas = "< 1"
                context = {
                    "ip": ip,
                    "bloqueo": bloqueo,
                    "horas_restantes": horas,
                }
                try:
                    response = render(request, "errors/ip_blocked.html", context=context, status=403)
                except Exception:
                    response = HttpResponseForbidden(
                        f"Tu IP ({ip}) ha sido bloqueada temporalmente por medidas de seguridad. "
                        "Contacta a soporte."
                    )
                response["X-IP-Blocked"] = "1"
                return response

        response = self.get_response(request)

        try:
            if response.status_code == 403 and not skip_check:
                num_w, _ = contar_warnings_ventana(ip)
                response["X-Security-Warnings"] = str(num_w)
                if num_w > 0:
                    response["X-Security-Alert"] = "1"
        except Exception:
            pass

        return response

    def process_exception(self, request, exception):
        if isinstance(exception, PermissionError):
            try:
                registrar_evento(request, "security_warning", gravedad="warning")
            except Exception:
                pass
        return None
