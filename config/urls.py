from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, re_path
from django.views.generic.base import RedirectView


def redirect_password_reset_confirm(request, uidb64, token):
    return redirect("usuarios:password_reset_confirm", uidb64=uidb64, token=token)


urlpatterns = [
    path("admin/", admin.site.urls),
    # Licensing
    path("licensing/", include("apps.licensing.urls")),
    # Apps
    path("usuarios/", include("apps.usuarios.urls")),
    path("clientes/", include("apps.clientes.urls")),
    path("catalogo/", include("apps.catalogo.urls")),
    path("compras/", include("apps.compras.urls")),
    path("pedidos/", include("apps.pedidos.urls")),
    path("pagos/", include("apps.pagos.urls")),
    path("reportes/", include("apps.reportes.urls")),
    path("auditoria/", include("apps.auditoria.urls")),
    path("logistica/", include("apps.logistica.urls")),
    path("ia/", include("apps.ia.urls")),
    path("ayuda/", include("apps.ayuda.urls")),
    path("", include("apps.inicio.urls")),
    # ===== Redirecciones de recuperación de contraseña a usuarios =====
    path("password-reset/", lambda r: redirect("usuarios:password_reset"), name="password_reset"),
    path(
        "password-reset/done/",
        lambda r: redirect("usuarios:password_reset_done"),
        name="password_reset_done",
    ),
    path("reset/<uidb64>/<token>/", redirect_password_reset_confirm, name="password_reset_confirm"),
    path(
        "reset/done/",
        lambda r: redirect("usuarios:password_reset_complete"),
        name="password_reset_complete",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if "django_browser_reload" in settings.INSTALLED_APPS:
        urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
