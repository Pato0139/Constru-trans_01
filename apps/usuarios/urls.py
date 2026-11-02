from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "usuarios"

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
    path(
        "usuarios/toggle-estado/<int:id>/",
        views.toggle_estado_usuario,
        name="toggle_estado_usuario",
    ),
    path("usuarios/editar/<int:id>/", views.editar_usuario, name="editar_usuario"),
    path("perfil/admin/", views.perfil_admin, name="perfil_admin"),
    path("perfil/editar/", views.editar_perfil, name="editar_perfil"),
    path("conductores/", views.lista_conductores, name="lista_conductores"),
    path("conductores/crear/", views.crear_conductor, name="crear_conductor"),
    path("conductores/editar/<int:id>/", views.editar_conductor, name="editar_conductor"),
    path("conductores/detalle/<int:id>/", views.detalle_conductor, name="detalle_conductor"),
    path(
        "conductores/toggle-estado/<int:id>/",
        views.toggle_estado_conductor,
        name="toggle_estado_conductor",
    ),
    path("conductores/eliminar/<int:id>/", views.eliminar_conductor, name="eliminar_conductor"),
    path(
        "conductores/asignar-vehiculo/<int:conductor_id>/",
        views.asignar_vehiculo_conductor,
        name="asignar_vehiculo_conductor",
    ),
    # conductor
    path("panel-conductor/", views.panel_conductor, name="panel_conductor"),
    path("perfil-conductor/", views.perfil_conductor, name="perfil_conductor"),
    path("pedidos-conductor/", views.pedidos_conductor, name="pedidos_conductor"),
    path("mis-entregas/", views.mis_entregas, name="mis_entregas"),
    path("entregas/iniciar/<int:entrega_id>/", views.iniciar_entrega, name="iniciar_entrega"),
    path("entregas/finalizar/<int:entrega_id>/", views.finalizar_entrega, name="finalizar_entrega"),
    path(
        "entregas/detalle/<int:entrega_id>/",
        views.detalle_entrega_conductor,
        name="detalle_entrega_conductor",
    ),
    # Notificaciones
    path("notificaciones/", views.lista_notificaciones, name="notificaciones"),
    path(
        "notificaciones/marcar-leida/<int:id>/",
        views.marcar_notificacion_leida,
        name="marcar_notificacion_leida",
    ),
    # Configuraciones
    path("configuraciones/", views.configuraciones_usuario, name="configuraciones"),
    path("bd/cambiar/", views.cambiar_modo_bd, name="cambiar_modo_bd"),
    path("backup/descargar/", views.descargar_backup_db, name="descargar_backup"),
    # recuperar contraseña
    path(
        "recuperar/",
        views.CustomPasswordResetView.as_view(
            template_name="usuarios/recuperar_password.html",
            success_url=reverse_lazy("usuarios:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "recuperar/enviado/",
        auth_views.PasswordResetDoneView.as_view(template_name="usuarios/password_enviado.html"),
        name="password_reset_done",
    ),
    path(
        "recuperar/confirmar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="usuarios/password_confirmar.html",
            success_url=reverse_lazy("usuarios:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "recuperar/completo/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="usuarios/password_completo.html"
        ),
        name="password_reset_complete",
    ),
]
