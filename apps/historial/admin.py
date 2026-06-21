from django.contrib import admin

from .models import Historial


@admin.register(Historial)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'accion', 'modulo', 'elemento_id', 'fecha_hora')
    list_filter = ('accion', 'modulo', 'fecha_hora')
    search_fields = ('usuario__nombres', 'usuario__apellidos', 'modulo', 'elemento_id', 'descripcion')
    readonly_fields = ('fecha_hora',)