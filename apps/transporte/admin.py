# apps/transporte/admin.py
from django.contrib import admin
from .models import Entrega, HistorialEstadoEntrega

admin.site.register(Entrega)
admin.site.register(HistorialEstadoEntrega)