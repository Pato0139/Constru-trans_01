from django.contrib import admin

from .models import DetalleSolicitudPedido, SolicitudPedido


@admin.register(SolicitudPedido)
class SolicitudPedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "estado", "total", "fecha_creacion")
    list_filter = ("estado", "fecha_creacion")
    search_fields = ("cliente__nombres", "cliente__apellidos")
    readonly_fields = ("total", "fecha_creacion")


@admin.register(DetalleSolicitudPedido)
class DetalleSolicitudPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "material", "cantidad", "precio_unitario", "subtotal")
    search_fields = ("material__nombre",)
    raw_id_fields = ("pedido",)
