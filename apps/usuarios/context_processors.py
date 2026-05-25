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
                unread_ids = list(
                    Notificacion.objects.filter(usuario=usuario, leida=False)
                    .values_list('id', flat=True)[:10]
                )
                unread_count = len(unread_ids)

                recientes_ids = list(
                    Notificacion.objects.filter(usuario=usuario)
                    .order_by('-fecha')
                    .values_list('id', flat=True)[:5]
                )

                if recientes_ids:
                    recientes = list(
                        Notificacion.objects.filter(id__in=recientes_ids)
                        .only('id', 'titulo', 'mensaje', 'fecha', 'leida', 'tipo', 'link')
                    )
                else:
                    recientes = []

                data = {
                    'notif_recent': recientes,
                    'notif_unread_count': unread_count,
                }
                cache.set(cache_key, data, 300)
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
