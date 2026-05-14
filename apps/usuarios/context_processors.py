from .models import Notificacion
from django.core.cache import cache

def notificaciones_context(request):
    if request.user.is_authenticated:
        cache_key = f'notif_user_{request.user.id}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
            
        try:
            # Usamos select_related para evitar queries extras si se accede al user desde la notificacion
            # Y verificamos si el usuario tiene el perfil 'usuario'
            if hasattr(request.user, 'usuario'):
                usuario = request.user.usuario
                notificaciones = Notificacion.objects.filter(usuario=usuario).only('id', 'mensaje', 'fecha', 'leida', 'tipo').order_by('-fecha')
                unread_count = notificaciones.filter(leida=False).count()
                
                data = {
                    'notif_recent': list(notificaciones[:5]), # Convertimos a lista para cachear
                    'notif_unread_count': unread_count,
                }
                # Cacheamos por 60 segundos
                cache.set(cache_key, data, 60)
                return data
        except Exception:
            pass
            
    return {
        'notif_recent': [],
        'notif_unread_count': 0,
    }
