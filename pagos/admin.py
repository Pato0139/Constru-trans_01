from django.contrib import admin

from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
<<<<<<< HEAD
    list_display = ("id", "pedido", "monto", "metodo", "estado", "fecha_registro")
    list_filter = ("estado", "metodo")
    search_fields = ("=id", "=pedido__codigo_pedido", "referencia")
=======
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
>>>>>>> 49984237c7825998944fb40ba7acb96be2e3d525
