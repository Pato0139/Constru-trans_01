from django.contrib import admin
from .models import (
    EPS,
    Catalogo,
    Conductor,
    ConductorVehiculo,
    MaterialConstruccion,
    MetodoPago,
    Notificacion,
    Proveedor,
    Stock,
    UnidadMedida,
    Usuario,
    Vehiculo,
    HistorialPrecioMaterial,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("nombres", "apellidos", "get_email", "documento", "rol", "estado", "intentos_fallidos", "nivel_bloqueo")
    list_filter = ("rol", "estado", "tipo_documento", "nivel_bloqueo")
    search_fields = ("nombres", "apellidos", "documento")
    readonly_fields = ("intentos_fallidos", "bloqueado_hasta", "nivel_bloqueo")

    def get_email(self, obj):
        return obj.email

    get_email.short_description = "Correo"


# =====================================================================
# UNIDAD DE MEDIDA
# =====================================================================
@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "abreviatura", "activa", "orden")
    list_filter = ("activa",)
    search_fields = ("codigo", "nombre", "abreviatura")
    ordering = ("orden", "nombre")
    readonly_fields = ("fecha_creacion",)

    fieldsets = (
        ("Información Básica", {"fields": ("codigo", "nombre", "abreviatura", "descripcion")}),
        ("Control", {"fields": ("activa", "orden", "fecha_creacion"), "classes": ("collapse",)}),
    )


# =====================================================================
# MATERIAL CONSTRUCCION
# =====================================================================
@admin.register(MaterialConstruccion)
class MaterialConstruccionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "unidad_medida", "precio_referencia", "activo", "sincronizado")
    list_filter = ("activo", "unidad_medida", "catalogo")
    list_editable = ("activo",)
    search_fields = ("nombre", "descripcion")


# =====================================================================
# HISTORIAL PRECIO
# =====================================================================
class HistorialPrecioMaterialInline(admin.TabularInline):
    model = HistorialPrecioMaterial
    extra = 0
    readonly_fields = ("fecha_cambio", "precio_anterior", "precio_nuevo", "mes", "año")
    can_delete = False


@admin.register(HistorialPrecioMaterial)
class HistorialPrecioMaterialAdmin(admin.ModelAdmin):
    list_display = ("material", "precio_anterior", "precio_nuevo", "fecha_cambio", "mes", "año")
    list_filter = ("mes", "año", "material")
    search_fields = ("material__nombre", "observaciones")
    readonly_fields = ("fecha_cambio", "mes", "año")
    date_hierarchy = "fecha_cambio"


# Registra los demás:
admin.site.register(EPS)
admin.site.register(Conductor)
admin.site.register(Vehiculo)
admin.site.register(ConductorVehiculo)
admin.site.register(Catalogo)
admin.site.register(Proveedor)
admin.site.register(Stock)
admin.site.register(MetodoPago)
admin.site.register(Notificacion)
