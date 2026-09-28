from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    path("lista/", views.lista_pedidos_admin, name="lista_pedidos_admin"),
    path("entregas/", views.lista_entregas_admin, name="lista_entregas_admin"),
    path("detalle/<int:id>/", views.ver_pedido_admin, name="ver_pedido_admin"),
    path("entregas/crear/<int:orden_id>/", views.crear_entrega, name="crear_entrega"),
    path("eliminar/<int:id>/", views.eliminar_orden, name="eliminar_orden"),
    path("agregar-materiales/<int:id>/", views.agregar_materiales, name="agregar_materiales"),
    path("eliminar-detalle/<int:id>/", views.eliminar_detalle, name="eliminar_detalle"),
    path("calcular-total/<int:id>/", views.calcular_total, name="calcular_total"),
    path("solicitudes/crear/", views.crear_pedido, name="crear_solicitud"),
    path("solicitudes/", views.listar_pedidos, name="lista_solicitudes"),
    path("solicitudes/<int:pk>/", views.detalle_pedido, name="detalle_solicitud"),
    path("solicitudes/<int:pk>/aprobar/", views.aprobar_pedido, name="aprobar_solicitud"),
    path("solicitudes/<int:pk>/cancelar/", views.cancelar_pedido, name="cancelar_solicitud"),
]
