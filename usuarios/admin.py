from django.contrib import admin
from .models import (
    EPS,
    Conductor,
    Notificacion,
    Rol,
    Usuario,
    UsuarioRol,
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


admin.site.register(EPS)
admin.site.register(Conductor)
admin.site.register(Notificacion)
admin.site.register(Rol)
admin.site.register(UsuarioRol)
