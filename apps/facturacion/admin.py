from django.contrib import admin
from .models import Factura, Pago

class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    readonly_fields = ('fecha',)

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'cliente', 'total', 'estado', 'fecha_emision')
    list_filter = ('estado', 'fecha_emision')
    search_fields = ('numero', 'cliente__nombres', 'cliente__apellidos')
    inlines = [PagoInline]
    readonly_fields = ('numero', 'orden', 'cliente', 'fecha_emision', 'subtotal', 'iva', 'total')

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('factura', 'monto', 'metodo', 'fecha', 'registrado_por')
    list_filter = ('metodo', 'fecha')
    search_fields = ('factura__numero', 'referencia')
    readonly_fields = ('fecha',)
