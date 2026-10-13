from django.contrib import admin

from core.models import BloqueoIP, Historial, HistorialReporte, Reporte, SecurityEvent


@admin.register(Historial)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ("usuario", "accion", "modulo", "elemento_id", "fecha_hora")
    list_filter = ("accion", "modulo", "fecha_hora")
    search_fields = (
        "usuario__nombres",
        "usuario__apellidos",
        "modulo",
        "elemento_id",
        "descripcion",
    )
    readonly_fields = ("fecha_hora",)


@admin.register(BloqueoIP)
class BloqueoIPAdmin(admin.ModelAdmin):
    list_display = ("ip", "tipo", "activo", "creado_en", "expira_en")
    list_filter = ("activo", "tipo")
    search_fields = ("ip", "motivo")


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("tipo", "gravedad", "ip", "usuario", "creado_en")
    list_filter = ("tipo", "gravedad", "creado_en")
    search_fields = ("ip", "username_str", "path")


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
