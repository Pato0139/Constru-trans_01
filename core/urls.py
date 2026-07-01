from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


def redirect_password_reset_confirm(request, uidb64, token):
    return redirect("usuarios:password_reset_confirm", uidb64=uidb64, token=token)


urlpatterns = [
    path("admin/", admin.site.urls),
    # Licensing
    path("licensing/", include("licensing.urls")),
    # Apps
    path("usuarios/", include("usuarios.urls")),
    path("clientes/", include("clientes.urls")),
    path("inventario/", include("inventario.urls")),
    path("compras/", include("compras.urls")),
    path("ordenes/", include("ordenes.urls")),
    path("pedidos/", include("gestion_pedidos.urls")),
    path("facturacion/", include("facturacion.urls")),
    path("pagos/", include("pagos.urls")),
    path("reportes/", include("reportes.urls")),
    path("historial/", include("historial.urls")),
    path("transporte/", include("transporte.urls")),
    path("ia/", include("ia.urls")),
    path("", include("inicio.urls")),
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
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]
