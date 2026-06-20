from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('id_pago', 'factura', 'monto', 'fecha', 'codigo_metodo_pago', 'registrado_por')
    list_filter = ('fecha', 'codigo_metodo_pago')
    search_fields = ('factura__id_factura', 'referencia')
    readonly_fields = ('fecha',)
