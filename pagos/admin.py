from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "monto", "metodo", "estado", "fecha_registro")
    list_filter = ("estado", "metodo")
    search_fields = ("=id", "=pedido__codigo_pedido", "referencia")
