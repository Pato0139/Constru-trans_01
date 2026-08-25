from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from usuarios.models_permisos import usuario_tiene_permiso


def requiere_funcion(funcion: str):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not getattr(request.user, "is_authenticated", False):
                raise PermissionDenied("Debes iniciar sesión.")
            if not usuario_tiene_permiso(request.user, funcion):
                raise PermissionDenied(f"No tienes permiso: {funcion}")
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def combinar_funciones(*funciones):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not getattr(request.user, "is_authenticated", False):
                raise PermissionDenied("Debes iniciar sesión.")
            if any(usuario_tiene_permiso(request.user, f) for f in funciones):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied("No tienes ninguno de los permisos requeridos: %s" % ", ".join(funciones))
        return _wrapped
    return decorator