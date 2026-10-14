from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm


class ConstruTransAdminAuthenticationForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        if user.is_active and getattr(user, "rol", None) == "admin":
            return
        super().confirm_login_allowed(user)


class ConstruTransAdminSite(AdminSite):
    login_form = ConstruTransAdminAuthenticationForm

    def has_permission(self, request):
        if super().has_permission(request):
            return True
        user = request.user
        return bool(user.is_active and getattr(user, "rol", None) == "admin")
