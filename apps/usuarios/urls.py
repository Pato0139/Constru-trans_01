from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views

app_name = 'usuarios'

urlpatterns = [
    # auth
    path("login/", views.login_usuario, name="login"),
    path("registro/", views.registro, name="registro"),
    path("panel/", views.panel, name="panel"),
    path("logout/", views.cerrar_sesion, name="logout"),

    # admin
    path("usuarios/", views.lista_usuarios, name="lista_usuarios"),
    path("usuarios/crear/", views.crear_usuario, name="crear_usuario"),
    path("usuarios/eliminar/<int:id>/", views.eliminar_usuario, name="eliminar_usuario"),
    path("usuarios/editar/<int:id>/", views.editar_usuario, name="editar_usuario"),

    path("perfil/admin/", views.perfil_admin, name="perfil_admin"),
    path("perfil/editar/", views.editar_perfil, name="editar_perfil"),

    path("conductores/", views.lista_conductores, name="lista_conductores"),

    # conductor
    path("panel-conductor/", views.panel_conductor, name="panel_conductor"),
    path("perfil-conductor/", views.perfil_conductor, name="perfil_conductor"),
    path("pedidos-conductor/", views.pedidos_conductor, name="pedidos_conductor"),
    path("mis-entregas/", views.mis_entregas, name="mis_entregas"),

    # Notificaciones
    path("notificaciones/", views.lista_notificaciones, name="notificaciones"),
    path("notificaciones/marcar-leida/<int:id>/", views.marcar_notificacion_leida, name="marcar_notificacion_leida"),

    # recuperar contraseña
    path(
        "recuperar/",
        views.CustomPasswordResetView.as_view(
            template_name="usuarios/recuperar_password.html",
            email_template_name="registration/password_reset_email.html",
            success_url=reverse_lazy("usuarios:password_reset_done")
        ),
        name="password_reset"
    ),
    path(
        "recuperar/enviado/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="usuarios/password_enviado.html"
        ),
        name="password_reset_done"
    ),
    path(
        "recuperar/confirmar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="usuarios/password_confirmar.html",
            success_url=reverse_lazy("usuarios:password_reset_complete")
        ),
        name="password_reset_confirm"
    ),
    path(
        "recuperar/completo/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="usuarios/password_completo.html"
        ),
        name="password_reset_complete"
    ),
]
