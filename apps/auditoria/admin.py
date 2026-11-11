from django.contrib import admin

from .models import Historial


@admin.register(Historial)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ("usuario", "accion", "modulo", "elemento_id", "fecha_hora")
    list_filter = ("accion", "modulo", "fecha_hora")
    search_fields = (
        "usuario__nombres",
        "usuario__apellidos",
        "modulo",
        "elemento_id",
        "descripcion",
    )
    readonly_fields = tuple(field.name for field in Historial._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
