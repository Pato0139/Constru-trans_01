import logging
from django.http import JsonResponse
from django.shortcuts import render

from config.views_reportes import *  # noqa: F401,F403

logger = logging.getLogger(__name__)


def inicio(request):
    return render(request, "inicio/home.html")


def error_400(request, exception=None):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": "Solicitud incorrecta.", "status": 400}, status=400)
    return render(request, "errors/400.html", status=400)


def error_403(request, exception=None):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": "Acceso denegado.", "status": 403}, status=403)
    return render(request, "errors/403.html", status=403)


def error_404(request, exception=None):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": "Recurso no encontrado.", "status": 404}, status=404)
    return render(request, "errors/404.html", status=404)


def error_500(request):
    logger.exception("Error interno no controlado (HTTP 500)")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"error": "Error interno del servidor.", "status": 500}, status=500)
    return render(request, "errors/500.html", status=500)
