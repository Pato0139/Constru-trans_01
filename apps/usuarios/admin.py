from django.contrib import admin
from .models import Usuario, Material, Vehiculo, Administrador, Conductor, Cliente, Stock

class BaseUsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'user_email', 'rol', 'documento', 'estado')
    list_filter = ('estado', 'tipo_documento')
    search_fields = ('nombres', 'apellidos', 'user__email', 'documento')
    list_per_page = 20
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Correo Electrónico'

@admin.register(Administrador)
class AdministradorAdmin(BaseUsuarioAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(rol='admin')

@admin.register(Conductor)
class ConductorAdmin(BaseUsuarioAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(rol='conductor')

@admin.register(Cliente)
class ClienteAdmin(BaseUsuarioAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(rol='cliente')

@admin.register(Usuario)
class UsuarioAdmin(BaseUsuarioAdmin):
    list_filter = ('rol', 'estado', 'tipo_documento')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'precio')
    list_filter = ('tipo',)
    search_fields = ('nombre', 'descripcion')

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('material', 'cantidad', 'ubicacion', 'ultima_actualizacion')
    list_filter = ('ubicacion',)
    search_fields = ('material__nombre',)

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('placa', 'tipo', 'capacidad', 'estado')
    list_filter = ('tipo', 'estado')
    search_fields = ('placa',)
