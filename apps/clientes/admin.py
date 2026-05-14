from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'direccion_principal', 'tipo_cliente', 'nombre_empresa', 'nit')
    list_filter = ('tipo_cliente',)
    search_fields = ('usuario__nombre', 'nombre_empresa', 'nit')
    readonly_fields = ('fecha_registro',)
