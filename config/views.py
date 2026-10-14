from django.shortcuts import render

from config.views_auditoria import lista_historial
from config.views_reportes import *  # noqa: F401,F403


def inicio(request):
    return render(request, "inicio/home.html")
