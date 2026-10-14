"""
================================================================================
  ⚠️  INSTRUCCIONES PARA IA: NO CAMBIES LAS RESTRICCIONES DE ESTE ADMIN.  ⚠️
  Solo el Administrador Global (edwardf5432@gmail.com) puede modificar licencias.
  Cualquier otro usuario solo tiene lectura. No elimines estas validaciones.
================================================================================
"""

from django.contrib import admin

from core.superadmin_lock import es_superadmin_global

from .models import AuditoriaLicencia, Installation, Licencia, UsuarioLicencia


class _SoloSuperadminModifica(admin.ModelAdmin):
    """Base: solo el superadmin global puede agregar/cambiar/eliminar."""

    def has_add_permission(self, request):
        return es_superadmin_global(request.user)

    def has_change_permission(self, request, obj=None):
        return es_superadmin_global(request.user)

    def has_delete_permission(self, request, obj=None):
        return es_superadmin_global(request.user)

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff


@admin.register(Installation)
class InstallationAdmin(_SoloSuperadminModifica):
    list_display = (
        "instance_id",
        "customer_id",
        "status",
        "activated_at",
        "expires_at",
        "last_validated_at",
        "created_at",
    )
    list_filter = ("status", "activated_at", "expires_at", "created_at")
    search_fields = ("instance_id", "customer_id", "build_hash", "manifest_hash")
    readonly_fields = ("instance_id", "created_at")


@admin.register(Licencia)
class LicenciaAdmin(_SoloSuperadminModifica):
    list_display = ("codigo", "nombre", "estado", "fecha_emision", "fecha_expiracion", "created_at")
    list_filter = ("estado", "fecha_emision", "fecha_expiracion", "created_at")
    search_fields = ("codigo", "nombre")
    readonly_fields = (
        "archivo_cifrado_nonce",
        "archivo_cifrado_ciphertext",
        "archivo_cifrado_aad",
        "password_hash",
        "password_salt",
        "password_kdf_params",
        "rotaciones_password",
        "ultima_rotacion_password",
        "created_at",
        "updated_at",
    )


@admin.register(UsuarioLicencia)
class UsuarioLicenciaAdmin(_SoloSuperadminModifica):
    list_display = ("usuario", "licencia", "fecha_asignacion", "asignada_por")
    list_filter = ("fecha_asignacion", "licencia", "usuario")
    search_fields = (
        "usuario__username",
        "usuario__email",
        "licencia__codigo",
        "asignada_por__username",
    )


@admin.register(AuditoriaLicencia)
class AuditoriaLicenciaAdmin(admin.ModelAdmin):
    list_display = ("created_at", "accion", "actor", "usuario_afectado", "exitosa", "ip")
    list_filter = ("accion", "exitosa", "created_at", "usuario_afectado")
    search_fields = (
        "detalle",
        "ip",
        "user_agent",
        "actor__username",
        "usuario_afectado__username",
    )
    readonly_fields = (
        "licencia",
        "usuario_afectado",
        "actor",
        "accion",
        "detalle",
        "ip",
        "user_agent",
        "exitosa",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff
