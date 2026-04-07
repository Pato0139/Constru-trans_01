from .models import Historial

def registrar_actividad(request, accion, modulo, elemento_id=None, descripcion=""):
    """
    Registra una acción en el historial de actividades del sistema.
    """
    usuario = request.user if request and request.user.is_authenticated else None
    ip_address = get_client_ip(request) if request else None
    
    Historial.objects.create(
        usuario=usuario,
        accion=accion,
        modulo=modulo,
        elemento_id=str(elemento_id) if elemento_id else None,
        descripcion=descripcion,
        ip_address=ip_address
    )

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
