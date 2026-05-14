
from django.contrib import admin
from .models import Rol, Usuario, EPS, Conductor, Vehiculo, ConductorVehiculo
from .models import Catalogo, Proveedor, MaterialConstruccion, Stock, MetodoPago, Notificacion


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id_rol', 'nombre_rol')
    search_fields = ('nombre_rol',)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'correo', 'documento', 'rol', 'estado')
    list_filter = ('rol', 'estado', 'tipo_documento')
    search_fields = ('nombre', 'correo', 'documento')


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
