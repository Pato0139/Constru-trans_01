from django.contrib import admin

from .models import Compra, DetalleCompra


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1
    readonly_fields = ("subtotal",)


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ("id_compra", "proveedor", "fecha_compra", "total_compra", "estado", "usuario")
    list_filter = ("estado", "fecha_compra")
    search_fields = ("id_compra", "proveedor__nombre_empresa")
    readonly_fields = ("total_compra", "fecha_compra")
    inlines = [DetalleCompraInline]


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id_detalle_compra",
        "compra",
        "material",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )
    list_filter = ("compra", "material")
    readonly_fields = ("subtotal",)
