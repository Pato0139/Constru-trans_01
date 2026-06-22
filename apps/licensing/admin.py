from django.contrib import admin

from .models import Installation


@admin.register(Installation)
class InstallationAdmin(admin.ModelAdmin):
    list_display = (
        "instance_id",
        "customer_id",
        "status",
        "activated_at",
        "expires_at",
        "last_validated_at",
    )
    list_filter = ("status", "activated_at", "expires_at")
    search_fields = ("customer_id", "build_hash", "manifest_hash")
    readonly_fields = ("instance_id", "created_at")
