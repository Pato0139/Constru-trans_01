from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rutas listas para login/logout/reset password
    path("accounts/", include("django.contrib.auth.urls")),

    path('', include('apps.inicio.urls')),    
    path('usuarios/', include('apps.usuarios.urls')),
    path('clientes/', include('apps.clientes.urls')),
    path('inventario/', include('apps.inventario.urls')),
    path('compras/', include('apps.compras.urls')),
    path('transporte/', include('apps.transporte.urls')),
    path('ordenes/', include('apps.ordenes.urls')),
    path('facturacion/', include('apps.facturacion.urls')),
    path('pagos/', include('apps.pagos.urls')),
    path('reportes/', include('apps.reportes.urls')),
    path('historial/', include('apps.historial.urls')),
    path('ayuda/', lambda r: render(r, 'ayuda.html'), name='ayuda'),
    path("__reload__/", include("django_browser_reload.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
