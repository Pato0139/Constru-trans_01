from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

from core import views as core_views


def redirect_password_reset_confirm(request, uidb64, token):
    return redirect("usuarios:password_reset_confirm", uidb64=uidb64, token=token)


urlpatterns = [
    path("admin/", admin.site.urls),
    # Licensing
    path("licensing/", include("licensing.urls")),
    # Apps
    path("usuarios/", include("usuarios.urls")),
    path("clientes/", include("clientes.urls")),
    path("catalogo/", include("catalogo.urls")),
    path("compras/", include("compras.urls")),
    path("pedidos/", include("pedidos.urls")),
    path("pagos/", include("pedidos.pagos_urls")),
    path("reportes/", include("core.reportes_urls")),
    path("auditoria/", include("core.auditoria_urls")),
    path("logistica/", include("logistica.urls")),
    path("ia/", include("ia.urls")),
    path("ayuda/", include("ayuda.urls")),
    path("", include(([path("", core_views.inicio, name="inicio")], "inicio"))),
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
