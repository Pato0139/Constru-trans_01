"""Formato uniforme de errores y traducción de IntegrityError.

Formato::

    {"error": "VALIDATION_ERROR",
     "detalles": [{"campo": "email", "mensaje": "..."}]}
"""

import logging

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.http import JsonResponse

logger = logging.getLogger(__name__)

CAMPO_GENERAL = "general"


def _items_desde_dict(errores):
    detalles = []
    for campo, mensajes in errores.items():
        nombre = CAMPO_GENERAL if campo in (NON_FIELD_ERRORS, "__all__", None) else campo
        if isinstance(mensajes, (str, ValidationError)):
            mensajes = [mensajes]
        for m in mensajes:
            if isinstance(m, ValidationError):
                for texto in m.messages:
                    detalles.append({"campo": nombre, "mensaje": str(texto)})
            elif isinstance(m, dict):  # form.errors.get_json_data()
                detalles.append({"campo": nombre, "mensaje": str(m.get("message", ""))})
            else:
                detalles.append({"campo": nombre, "mensaje": str(m)})
    return detalles


def formatear_errores(origen):
    """Acepta ValidationError, form.errors (ErrorDict) o dict. Devuelve TODOS los errores."""
    if isinstance(origen, ValidationError):
        if hasattr(origen, "error_dict"):
            return _items_desde_dict(origen.error_dict)
        return [{"campo": CAMPO_GENERAL, "mensaje": str(m)} for m in origen.messages]
    if hasattr(origen, "get_json_data"):
        return _items_desde_dict(origen.get_json_data())
    if isinstance(origen, dict):
        return _items_desde_dict(origen)
    return [{"campo": CAMPO_GENERAL, "mensaje": str(origen)}]


def respuesta_validacion(origen, status=400):
    return JsonResponse(
        {"error": "VALIDATION_ERROR", "detalles": formatear_errores(origen)},
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )


def mensaje_integrity_error(exc):
    """Traduce un IntegrityError a un mensaje seguro (sin tablas ni SQL)."""
    texto = str(exc).lower()
    logger.warning("IntegrityError capturado: %s", exc)
    if "unique" in texto or "duplicate" in texto or "duplicad" in texto:
        return "Ya existe un registro con esos datos. Verifica los valores únicos."
    if "foreign key" in texto or "llave foránea" in texto:
        return "El registro está relacionado con otros datos o hace referencia a uno inexistente."
    if "check" in texto:
        return "Uno o más valores están fuera del rango permitido."
    if "not null" in texto or "null value" in texto:
        return "Falta un dato obligatorio."
    return "No fue posible guardar la información por una restricción de integridad."


def respuesta_integridad(exc):
    return JsonResponse(
        {
            "error": "INTEGRITY_ERROR",
            "detalles": [{"campo": CAMPO_GENERAL, "mensaje": mensaje_integrity_error(exc)}],
        },
        status=409,
        json_dumps_params={"ensure_ascii": False},
    )
