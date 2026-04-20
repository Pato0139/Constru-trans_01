from django.contrib import admin
from .models import Orden, Entrega, DetalleOrden

class DetalleOrdenInline(admin.TabularInline):
    model = DetalleOrden
    extra = 0

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente_nombre', 'precio', 'estado', 'fecha')
    list_filter = ('estado', 'fecha')
    search_fields = ('cliente__nombres', 'cliente__apellidos', 'direccion_destino')
    inlines = [DetalleOrdenInline]
    list_per_page = 20
    
    def cliente_nombre(self, obj):
        return f"{obj.cliente.nombres} {obj.cliente.apellidos}"
    cliente_nombre.short_description = 'Cliente'

@admin.register(Entrega)
class EntregaAdmin(admin.ModelAdmin):
    list_display = ('id', 'pedido', 'conductor', 'vehiculo', 'fecha')
    list_filter = ('fecha',)
    search_fields = ('conductor__nombres', 'conductor__apellidos', 'vehiculo__placa')
