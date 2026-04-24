from django.contrib import admin
from .models import Pago

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('factura', 'monto', 'metodo', 'fecha', 'registrado_por')
    list_filter = ('metodo', 'fecha')
    search_fields = ('factura__numero', 'referencia')
    readonly_fields = ('fecha',)
