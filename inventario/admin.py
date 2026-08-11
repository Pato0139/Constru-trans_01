from django.contrib import admin

from .models import ConteoItem, LoteMaterial, MovimientoInventario, SesionConteo


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ("id_movimiento", "material", "tipo_movimiento", "cantidad", "fecha_movimiento", "usuario")
    list_filter = ("tipo_movimiento", "fecha_movimiento", "material")
    search_fields = ("material__nombre", "observacion")
    readonly_fields = ("fecha_movimiento",)


@admin.register(LoteMaterial)
class LoteMaterialAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_lote",
        "material",
        "cantidad",
        "fecha_entrada",
        "fecha_vencimiento",
        "activo",
    )
    list_filter = ("activo", "material", "fecha_entrada")
    search_fields = ("codigo_lote", "material__nombre")
    readonly_fields = ("fecha_entrada",)


class ConteoItemInline(admin.TabularInline):
    model = ConteoItem
    extra = 0
    readonly_fields = ("diferencia",)


@admin.register(SesionConteo)
class SesionConteoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "estado", "fecha_inicio", "fecha_fin", "usuario_responsable")
    list_filter = ("estado", "fecha_inicio")
    search_fields = ("codigo", "observaciones")
    readonly_fields = ("fecha_inicio",)
    inlines = [ConteoItemInline]


@admin.register(ConteoItem)
class ConteoItemAdmin(admin.ModelAdmin):
    list_display = (
        "sesion",
        "material",
        "cantidad_sistema",
        "cantidad_fisica",
        "diferencia",
        "fecha_conteo",
    )
    list_filter = ("sesion", "material", "fecha_conteo")
    search_fields = ("sesion__codigo", "material__nombre")
    readonly_fields = ("diferencia", "fecha_conteo")
