from django.contrib import admin

from .models import Factura


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = (
        "id_factura",
        "pedido",
        "fecha",
        "total",
        "estado",
        "total_pagado",
        "saldo_pendiente",
    )
    list_filter = ("estado", "fecha")
    search_fields = ("id_factura", "pedido__codigo_pedido")
    readonly_fields = ("fecha", "total_pagado", "saldo_pendiente")
