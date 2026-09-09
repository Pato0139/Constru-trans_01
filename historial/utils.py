import logging

from django.db import IntegrityError

from .models import Historial

logger = logging.getLogger(__name__)


def registrar_actividad(request, accion, modulo, elemento_id=None, descripcion=""):
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
    except IntegrityError:
        # El historial no debe revertir una operación válida si el usuario
        # pertenece a otra base de datos que la seleccionada para auditoría.
        logger.warning("No se pudo asociar el usuario al historial; se guardará sin usuario.")
        datos["usuario"] = None
        Historial.objects.create(**datos)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
