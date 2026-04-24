from django.contrib import admin
from .models import Factura
from apps.pagos.models import Pago

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
