from django.urls import path
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [

    path("login/", views.login_usuario, name="login"),
    path("registro/", views.registro, name="registro"),
    path("panel/", views.panel, name="panel"),
    path("logout/", views.cerrar_sesion, name="logout"),

    path("usuarios/", views.lista_usuarios, name="lista_usuarios"),
    path("eliminar/<int:id>/", views.eliminar_usuario, name="eliminar_usuario"),
    path("editar/<int:id>/", views.editar_usuario, name="editar_usuario"),
    path("conductores/", views.lista_conductores, name="lista_conductores"),
    path("vehiculos/", views.lista_vehiculos, name="lista_vehiculos"),
    path("reportes/", views.reportes_admin, name="reportes_admin"),

    path("cliente/", views.panel_cliente, name="panel_cliente"),
    path("perfil/", views.perfil_cliente, name="perfil_cliente"),

    path("pedido/crear/", views.crear_pedido, name="crear_pedido"),
    path("mis-pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("seguimiento/", views.seguimiento_pedidos, name="seguimiento_pedidos"),
    path("historial/", views.historial_pedidos, name="historial_pedidos"),

    path("materiales/", views.lista_materiales, name="lista_materiales"),
    path("materiales/crear/", views.crear_material, name="crear_material"),
    path("materiales/editar/<int:id>/", views.editar_material, name="editar_material"),
    path("materiales/eliminar/<int:id>/", views.eliminar_material, name="eliminar_material"),

   # PANEL CONDUCTOR
path("panel-conductor/", views.panel_conductor, name="panel_conductor"),
path("perfil-conductor/", views.perfil_conductor, name="perfil_conductor"),

# pedidos activos
path("pedidos/", views.pedidos_conductor, name="pedidos_conductor"),

# historial de entregas
path("mis-entregas/", views.mis_entregas, name="mis_entregas"),
    # RECUPERAR CONTRASEÑA
    path(
        "recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="usuarios/recuperar_password.html"
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
        "recuperar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="usuarios/password_confirmar.html"
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