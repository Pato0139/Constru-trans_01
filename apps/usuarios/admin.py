from django.contrib import admin
from .models import (
    Usuario, Administrador, Conductor, Cliente,
    PerfilConductor, EPS, ConductorVehiculo, Vehiculo,
    Catalogo, Proveedor, Material, Stock, Notificacion
)


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


@admin.register(EPS)
class EPSAdmin(admin.ModelAdmin):
    list_display = ('codigo_eps', 'nombre_eps', 'ciudad', 'telefono')
    search_fields = ('nombre_eps', 'codigo_eps')


@admin.register(PerfilConductor)
class PerfilConductorAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'numero_licencia', 'categoria_licencia', 'tipo_licencia', 'eps', 'fecha_ingreso')
    list_filter = ('categoria_licencia', 'tipo_licencia', 'eps')
    search_fields = ('usuario__nombres', 'usuario__apellidos', 'numero_licencia')


@admin.register(ConductorVehiculo)
class ConductorVehiculoAdmin(admin.ModelAdmin):
    list_display = ('conductor', 'vehiculo', 'fecha_asignacion', 'fecha_fin')
    list_filter = ('fecha_asignacion',)
    search_fields = ('conductor__nombres', 'conductor__apellidos', 'vehiculo__placa')


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('placa', 'marca', 'modelo', 'tipo_vehiculo', 'capacidad_carga', 'estado')
    list_filter = ('tipo_vehiculo', 'estado', 'tipo_adquisicion')
    search_fields = ('placa', 'marca', 'modelo')


@admin.register(Catalogo)
class CatalogoAdmin(admin.ModelAdmin):
    list_display = ('codigo_catalogo', 'nombre_empresa')
    search_fields = ('nombre_empresa', 'codigo_catalogo')


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'nit', 'contacto_nombre', 'telefono')
    search_fields = ('nombre_empresa', 'nit')


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'marca', 'unidad_medida', 'precio_referencia')
    list_filter = ('tipo', 'marca', 'catalogo')
    search_fields = ('nombre', 'descripcion')


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('material', 'cantidad', 'stock_minimo', 'ubicacion', 'ultima_actualizacion')
    list_filter = ('ubicacion',)
    search_fields = ('material__nombre',)


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'titulo', 'tipo', 'leida', 'fecha')
    list_filter = ('tipo', 'leida', 'fecha')
    search_fields = ('titulo', 'mensaje')
