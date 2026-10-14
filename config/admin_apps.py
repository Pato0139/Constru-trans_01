from django.contrib.admin.apps import AdminConfig


class ConstruTransAdminConfig(AdminConfig):
    default_site = "config.admin_site.ConstruTransAdminSite"
