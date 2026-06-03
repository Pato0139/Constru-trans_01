
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
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'get_email', 'documento', 'rol', 'estado')
    list_filter = ('rol', 'estado', 'tipo_documento')
    search_fields = ('nombres', 'apellidos', 'documento')

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Correo'


# =====================================================================
# UNIDAD DE MEDIDA - Tabla de Referencia Normalizada
# =====================================================================
@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'abreviatura', 'activa', 'orden')
    list_filter = ('activa',)
    search_fields = ('codigo', 'nombre', 'abreviatura')
    ordering = ('orden', 'nombre')
    readonly_fields = ('fecha_creacion',)
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'abreviatura', 'descripcion')
        }),
        ('Control', {
            'fields': ('activa', 'orden', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )


# Registra los demás:
admin.site.register(EPS)
admin.site.register(Conductor)
admin.site.register(Vehiculo)
admin.site.register(ConductorVehiculo)
admin.site.register(Catalogo)
admin.site.register(Proveedor)
admin.site.register(MaterialConstruccion)
admin.site.register(Stock)
admin.site.register(MetodoPago)
admin.site.register(Notificacion)
