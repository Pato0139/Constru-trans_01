from django.contrib import admin
from .models import Reporte, HistorialReporte


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ('numero_reporte', 'tipo', 'fecha_generada', 'estado', 'generado_por')
    list_filter = ('tipo', 'estado', 'fecha_generada')
    search_fields = ('numero_reporte', 'descripcion')

@admin.register(HistorialReporte)
class HistorialReporteAdmin(admin.ModelAdmin):
    list_display = ('reporte', 'codigo_historia', 'fecha_reporte')
    list_filter = ('fecha_reporte',)
    search_fields = ('codigo_historia', 'descripcion')
