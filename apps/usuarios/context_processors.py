from django.core.cache import cache

from apps.usuarios.models import Notificacion
from core.utils import conexion_remota_disponible


def notificaciones_context(request):
    if request.user.is_authenticated:
        cache_key = f'notif_user_{request.user.id}'
        cached_data = cache.get(cache_key)

        if cached_data:
            return cached_data

        try:
            if hasattr(request.user, 'usuario'):
                usuario = request.user.usuario
                notificaciones = Notificacion.objects.filter(usuario=usuario).only('id', 'mensaje', 'fecha', 'leida', 'tipo').order_by('-fecha')
                unread_count = notificaciones.filter(leida=False).count()

                data = {
                    'notif_recent': list(notificaciones[:5]),
                    'notif_unread_count': unread_count,
                }
                cache.set(cache_key, data, 60)
                return data
        except Exception:
            pass

    return {
        'notif_recent': [],
        'notif_unread_count': 0,
    }


def modo_context(request):
    """Agrega modo_local y modo_invitado al contexto de todas las plantillas."""
    modo_local = not conexion_remota_disponible()
    modo_invitado = modo_local and (not request.user.is_authenticated or not hasattr(request.user, 'usuario'))
    return {
        'modo_local': modo_local,
        'modo_invitado': modo_invitado,
    }
