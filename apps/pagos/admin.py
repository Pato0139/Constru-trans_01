from django.contrib import admin

from .models import DetallePago, Factura, Pago, PagoFactura


@admin.register(DetallePago)
class DetallePagoAdmin(admin.ModelAdmin):
    list_display = ("id", "pago", "concepto", "monto")
    search_fields = ("concepto", "pago__pedido__codigo_pedido")
    list_select_related = ("pago",)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)


class PagoFacturaInline(admin.TabularInline):
    model = PagoFactura
    extra = 0
    readonly_fields = ["fecha_registro", "fecha_revision", "registrado_por", "revisado_por"]
    fk_name = "factura"


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
    list_select_related = ("pedido", "revisado_por")

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ["numero", "pedido", "cliente", "fecha_emision", "total", "estado"]
    list_filter = ["estado", "fecha_emision"]
    search_fields = ["numero", "pedido__codigo_pedido", "cliente__usuario__nombres"]
    readonly_fields = ["numero", "uuid_publico"]
    inlines = [PagoFacturaInline]
    list_select_related = ("pedido", "cliente__usuario")

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)


@admin.register(PagoFactura)
class PagoFacturaAdmin(admin.ModelAdmin):
    list_display = [
        "factura",
        "monto",
        "metodo",
        "estado",
        "fecha_registro",
        "registrado_por",
    ]
    list_filter = ["estado", "metodo", "fecha_registro"]
    search_fields = [
        "factura__numero",
        "referencia",
        "factura__pedido__codigo_pedido",
    ]
    readonly_fields = ["fecha_registro", "fecha_revision"]
    list_select_related = ("factura", "registrado_por")

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)
