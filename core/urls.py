from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rutas de recuperación de contraseña fuera del namespace para evitar NoReverseMatch
    path('usuarios/recuperar/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name="usuarios/password_confirmar.html", success_url="/usuarios/recuperar/completo/"), 
         name='password_reset_confirm'),
    path('usuarios/recuperar/completo/', 
         auth_views.PasswordResetCompleteView.as_view(template_name="usuarios/password_completo.html"), 
         name='password_reset_complete'),

    path('', include('apps.inicio.urls')),    
    path('usuarios/', include('apps.usuarios.urls')),
    path('clientes/', include('apps.clientes.urls')),
    path('inventario/', include('apps.inventario.urls')),
    path('compras/', include('apps.compras.urls')),
    path('transporte/', include('apps.transporte.urls')),
    path('ordenes/', include('apps.ordenes.urls')),
    path('facturacion/', include('apps.facturacion.urls')),
    path('reportes/', include('apps.reportes.urls')),
    path('historial/', include('historial.urls')),
    path('ayuda/', lambda r: render(r, 'ayuda.html'), name='ayuda'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
