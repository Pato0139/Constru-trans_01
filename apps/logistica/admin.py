from django.contrib import admin

from .models import (ConductorVehiculo, Entrega, Novedad, RespuestaSeguimiento,
                     Seguimiento, Vehiculo)


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = (
        "id_vehiculo", "placa", "marca", "modelo", "tipo_vehiculo",
        "capacidad_carga", "estado", "sincronizado",
    )
    search_fields = ("placa", "marca", "modelo", "tipo_vehiculo")
    list_filter = ("estado", "sincronizado", "fecha_registro")


@admin.register(ConductorVehiculo)
class ConductorVehiculoAdmin(admin.ModelAdmin):
    list_display = ("conductor", "vehiculo", "fecha_asignacion", "fecha_fin")
    search_fields = ("conductor__usuario__nombres", "conductor__usuario__apellidos", "vehiculo__placa")
    list_filter = ("fecha_asignacion", "fecha_fin")
    list_select_related = ("conductor__usuario", "vehiculo")


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = (
        "id_entrega", "pedido", "conductor", "vehiculo", "estado",
        "direccion_entrega", "fecha_salida", "fecha_entrega", "sincronizado",
    )
    search_fields = (
        "direccion_entrega",
        "conductor__usuario__nombres",
        "conductor__usuario__apellidos",
        "vehiculo__placa",
    )
    list_filter = ("estado", "sincronizado", "fecha_salida", "fecha_entrega")
    list_select_related = ("conductor__usuario", "vehiculo", "pedido")


@admin.register(Novedad)
class NovedadAdmin(admin.ModelAdmin):
    list_display = (
        "id_novedad", "entrega", "tipo", "estado", "fecha_generada",
        "fecha_cierre", "reportado_por",
    )
    search_fields = ("descripcion", "reportado_por__username")
    list_filter = ("tipo", "estado", "fecha_generada", "fecha_cierre")
    list_select_related = ("entrega", "reportado_por")


@admin.register(Seguimiento)
class SeguimientoAdmin(admin.ModelAdmin):
    list_display = (
        "id_seguimiento", "novedad", "atendido_por",
        "fecha_seguimiento", "estado",
    )
    search_fields = ("comentario", "atendido_por__username")
    list_filter = ("estado", "fecha_seguimiento")
    list_select_related = ("novedad", "atendido_por")


@admin.register(RespuestaSeguimiento)
class RespuestaSeguimientoAdmin(admin.ModelAdmin):
    list_display = (
        "id_respuesta", "seguimiento", "redactada_por",
        "fecha_respuesta", "estado",
    )
    search_fields = ("texto", "redactada_por__username")
    list_filter = ("estado", "fecha_respuesta")
    list_select_related = ("seguimiento", "redactada_por")
