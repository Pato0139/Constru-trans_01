from django.contrib import admin

from .models import HistorialReporte, Reporte


class HistorialReporteInline(admin.TabularInline):
    model = HistorialReporte
    extra = 0
    readonly_fields = ("fecha_reporte",)


@admin.register(Reporte)
class ReporteAdmin(admin.ModelAdmin):
    list_display = ("numero_reporte", "tipo", "fecha_generada", "estado", "usuario")
    list_filter = ("tipo", "estado", "fecha_generada")
    search_fields = ("numero_reporte", "descripcion")
    readonly_fields = ("fecha_generada",)
    inlines = [HistorialReporteInline]


@admin.register(HistorialReporte)
class HistorialReporteAdmin(admin.ModelAdmin):
    list_display = ("codigo_historia", "reporte", "fecha_reporte", "descripcion")
    list_filter = ("fecha_reporte",)
    search_fields = ("codigo_historia", "descripcion")
    readonly_fields = ("fecha_reporte",)
