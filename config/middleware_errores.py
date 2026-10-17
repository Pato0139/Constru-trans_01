"""Middleware que convierte ValidationError / IntegrityError no capturados en
respuestas controladas, sin exponer tablas, SQL ni stack traces.

- Peticiones AJAX/JSON → JSON {"error", "detalles"} con 400 / 409.
- Peticiones HTML → mensaje en español y redirección a la página anterior.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

from .errors import formatear_errores, mensaje_integrity_error, respuesta_integridad, respuesta_validacion


def _espera_json(request):
    return (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
        or request.content_type == "application/json"
    )


def _volver(request):
    destino = request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        destino = "/"
    return HttpResponseRedirect(destino)


class ValidationErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, ValidationError):
            if _espera_json(request):
                return respuesta_validacion(exception)
            for d in formatear_errores(exception):
                messages.error(request, d["mensaje"])
            return _volver(request)
        if isinstance(exception, IntegrityError):
            if _espera_json(request):
                return respuesta_integridad(exception)
            messages.error(request, mensaje_integrity_error(exception))
            return _volver(request)
        return None
