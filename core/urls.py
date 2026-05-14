from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render

urlpatterns = [
    path('admin/', admin.site.urls),

    # Apps
    path('usuarios/', include('apps.usuarios.urls')),
    path('clientes/', include('apps.clientes.urls')),
    path('inventario/', include('apps.inventario.urls')),
    path('compras/', include('apps.compras.urls')),
    path('ordenes/', include('apps.ordenes.urls')),
    path('facturacion/', include('apps.facturacion.urls')),
    path('pagos/', include('apps.pagos.urls')),
    path('reportes/', include('apps.reportes.urls')),
    path('historial/', include('apps.historial.urls')),
    path('', include('apps.inicio.urls')),

    # ===== Recuperación de contraseña (Django nativo) =====
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset_form.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'),
         name='password_reset'),

    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'),
         name='password_reset_done'),

    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'),
         name='password_reset_confirm'),

    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]
