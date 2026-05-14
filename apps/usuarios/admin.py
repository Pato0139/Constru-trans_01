
from django.contrib import admin
from .models import Usuario, EPS, Conductor, Vehiculo, ConductorVehiculo
from .models import Catalogo, Proveedor, MaterialConstruccion, Stock, MetodoPago, Notificacion


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'get_email', 'documento', 'rol', 'estado')
    list_filter = ('rol', 'estado', 'tipo_documento')
    search_fields = ('nombres', 'apellidos', 'documento')
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Correo'


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
