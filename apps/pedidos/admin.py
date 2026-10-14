from django.contrib import admin

from .models import (DetallePedido, DetalleSolicitudPedido, Pago, Pedido,
                     SolicitudPedido)


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1
    readonly_fields = ("subtotal",)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("codigo_pedido", "usuario", "fecha_solicitud", "total", "estado")
    list_filter = ("estado", "fecha_solicitud")
    search_fields = (
        "codigo_pedido",
        "usuario__nombres",
        "usuario__apellidos",
        "usuario__documento",
    )
    readonly_fields = ("total", "fecha_solicitud")
    inlines = [DetallePedidoInline]


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id_detalle_pedido",
        "pedido",
        "material",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    list_filter = ("pedido", "material")
    readonly_fields = ("subtotal",)


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


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pedido",
        "metodo",
        "monto",
        "estado",
        "fecha_registro",
        "revisado_por",
    )
    list_filter = ("estado", "metodo", "fecha_registro")
    search_fields = ("pedido__codigo_pedido", "observaciones")
    readonly_fields = ("fecha_registro", "fecha_revision")
