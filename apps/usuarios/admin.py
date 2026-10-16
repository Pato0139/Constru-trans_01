from django.contrib import admin

from .models import EPS, Conductor, Notificacion, Rol, Usuario, UsuarioRol


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = (
        "nombres",
        "apellidos",
        "get_email",
        "documento",
        "rol",
        "estado",
        "intentos_fallidos",
        "nivel_bloqueo",
    )
    list_filter = ("rol", "estado", "tipo_documento", "nivel_bloqueo")
    search_fields = ("nombres", "apellidos", "documento", "email", "username")
    readonly_fields = ("intentos_fallidos", "bloqueado_hasta", "nivel_bloqueo")

    def get_email(self, obj):
        return obj.email

    get_email.short_description = "Correo"


@admin.register(EPS)
class EPSAdmin(admin.ModelAdmin):
    list_display = ("codigo_eps", "numero_seguro", "ciudad", "telefono", "correo")
    search_fields = ("codigo_eps", "numero_seguro", "ciudad", "correo")


@admin.register(Conductor)
class ConductorAdmin(admin.ModelAdmin):
    list_display = (
        "usuario",
        "numero_licencia",
        "categoria_licencia",
        "estado",
        "fecha_vencimiento_licencia",
    )
    list_filter = ("estado", "categoria_licencia", "eps")
    search_fields = (
        "usuario__nombres",
        "usuario__apellidos",
        "usuario__documento",
        "numero_licencia",
    )


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "titulo", "tipo", "leida", "fecha")
    list_filter = ("tipo", "leida", "fecha")
    search_fields = ("titulo", "mensaje", "usuario__nombres", "usuario__apellidos")


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("nombre_rol", "descripcion", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre_rol", "descripcion")


@admin.register(UsuarioRol)
class UsuarioRolAdmin(admin.ModelAdmin):
    list_display = ("usuario", "rol", "fecha_asignacion", "fecha_revocacion", "activo")
    list_filter = ("activo", "rol", "fecha_asignacion")
    search_fields = ("usuario__nombres", "usuario__apellidos", "rol__nombre_rol")
