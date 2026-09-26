from django.contrib import admin

from .models import Pago


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
