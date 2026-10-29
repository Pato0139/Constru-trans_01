from django.contrib import admin

from config.models import BloqueoIP, SecurityEvent
from config.security import desbloquear_ip


@admin.register(BloqueoIP)
class BloqueoIPAdmin(admin.ModelAdmin):
    list_display = ("ip", "tipo", "activo", "creado_en", "expira_en")
    list_filter = ("activo", "tipo")
    search_fields = ("ip", "motivo")
    actions = ["desbloquear_ips_seleccionadas"]

    @admin.action(description="Desbloquear IPs seleccionadas")
    def desbloquear_ips_seleccionadas(self, request, queryset):
        count = 0
        for b in queryset:
            desbloquear_ip(b.ip)
            count += 1
        self.message_user(request, f"{count} IP(s) desbloqueada(s) correctamente.")


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display = ("tipo", "gravedad", "ip", "usuario", "creado_en")
    list_filter = ("tipo", "gravedad", "creado_en")
    search_fields = ("ip", "username_str", "path")
