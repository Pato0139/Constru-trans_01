from django.contrib import admin

from config.models import BloqueoIP, SecurityEvent


@admin.register(BloqueoIP)
class BloqueoIPAdmin(admin.ModelAdmin):
    list_display = ("ip", "tipo", "activo", "creado_en", "expira_en")
    list_filter = ("activo", "tipo")
    search_fields = ("ip", "motivo")


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("tipo", "gravedad", "ip", "usuario", "creado_en")
    list_filter = ("tipo", "gravedad", "creado_en")
    search_fields = ("ip", "username_str", "path")


def secure_admin_has_permission(request):
    """Exige que el usuario sea activo, staff y tenga rol 'admin' (o sea superuser)."""
    user = request.user
    if not (getattr(user, "is_active", False) and getattr(user, "is_staff", False)):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return getattr(user, "rol", "") == "admin"


admin.site.has_permission = secure_admin_has_permission
