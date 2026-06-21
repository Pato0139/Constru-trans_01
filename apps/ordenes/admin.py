from django.contrib import admin

from .models import DetallePedido, Entrega, Pedido


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1
    readonly_fields = ('subtotal',)


class EntregaInline(admin.TabularInline):
    model = Entrega
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('codigo_pedido', 'usuario', 'fecha_solicitud', 'total', 'estado')
    list_filter = ('estado', 'fecha_solicitud')
    search_fields = ('codigo_pedido', 'usuario__nombres', 'usuario__apellidos', 'usuario__documento')
    readonly_fields = ('total', 'fecha_solicitud')
    inlines = [DetallePedidoInline, EntregaInline]


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ('id_detalle_pedido', 'pedido', 'material', 'cantidad', 'precio_unitario', 'subtotal')
    list_filter = ('pedido', 'material')
    readonly_fields = ('subtotal',)


@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('id_entrega', 'pedido', 'conductor', 'vehiculo', 'estado', 'fecha_salida')
    list_filter = ('estado', 'fecha_salida')
    search_fields = ('pedido__codigo_pedido', 'conductor__usuario__nombres', 'conductor__usuario__apellidos', 'vehiculo__placa')
