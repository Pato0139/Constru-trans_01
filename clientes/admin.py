from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "direccion", "tipo_cliente", "nombre_empresa", "nit", "es_vip", "gasto_acumulado")
    list_filter = ("tipo_cliente", "es_vip", "fecha_registro")
    search_fields = (
        "usuario__nombres",
        "usuario__apellidos",
        "usuario__documento",
        "nombre_empresa",
        "nit",
        "direccion",
        "contacto_alternativo",
        "observaciones",
    )
    readonly_fields = ("fecha_registro",)
