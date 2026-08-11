from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("usuario", "direccion", "tipo_cliente", "nombre_empresa", "nit")
    list_filter = ("tipo_cliente",)
    search_fields = (
        "usuario__nombres",
        "usuario__apellidos",
        "usuario__documento",
        "nombre_empresa",
        "nit",
    )
    readonly_fields = ("fecha_registro",)
