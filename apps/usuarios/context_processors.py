from .models import Notificacion

def notificaciones_context(request):
    if request.user.is_authenticated:
        try:
            usuario = request.user.usuario
            notificaciones = Notificacion.objects.filter(usuario=usuario).order_by('-fecha')
            unread_count = notificaciones.filter(leida=False).count()
            return {
                'notif_recent': notificaciones[:5],
                'notif_unread_count': unread_count,
            }
        except:
            return {
                'notif_recent': [],
                'notif_unread_count': 0,
            }
    return {
        'notif_recent': [],
        'notif_unread_count': 0,
    }
