from django.contrib import admin

from .models import Compra, DetalleCompra, Proveedor, ProveedorMaterial


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1
    readonly_fields = ("subtotal",)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("codigo_proveedor", "nombre_empresa", "nit", "contacto_nombre", "telefono", "ciudad", "activo")
    list_filter = ("activo", "ciudad", "categoria")
    search_fields = ("nombre_empresa", "nit", "contacto_nombre", "correo")
    readonly_fields = ("fecha_registro", "codigo_proveedor")


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


@admin.register(ProveedorMaterial)
class ProveedorMaterialAdmin(admin.ModelAdmin):
    list_display = ("proveedor", "material", "precio_actual", "fecha_actualizacion", "activo")
    list_filter = ("activo", "proveedor")
    search_fields = ("proveedor__nombre_empresa", "material__nombre", "referencia_proveedor")
