from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path("panel/", views.panel_cliente, name="panel_cliente"),
    path("perfil/", views.perfil_cliente, name="perfil_cliente"),
    path("pedido/crear/", views.crear_pedido, name="crear_pedido"),
    path("pedido/editar/<int:id>/", views.editar_pedido, name="editar_pedido"),
    path("mis-pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("seguimiento/", views.seguimiento_pedidos, name="seguimiento_pedidos"),
    path("historial/", views.historial_pedidos, name="historial_pedidos"),
    path("orden/eliminar/<int:id>/", views.eliminar_orden, name="eliminar_orden"),
]
