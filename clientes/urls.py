from django.urls import path

from . import views

app_name = "clientes"

urlpatterns = [
    path("panel/", views.panel_cliente, name="panel_cliente"),
    path("perfil/", views.perfil_cliente, name="perfil_cliente"),
    path("pedido/crear/", views.crear_pedido, name="crear_pedido"),
    path("pedido/editar/<int:id>/", views.editar_pedido, name="editar_pedido"),
    path("mis-pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("mis-pagos/", views.mis_pagos, name="mis_pagos"),
    path("seguimiento/", views.seguimiento_pedidos, name="seguimiento_pedidos"),
    path("historial/", views.historial_pedidos, name="historial_pedidos"),
    path("orden/cancelar/<int:id>/", views.cancelar_pedido, name="cancelar_pedido"),
    
    # Rutas de administración
    path("admin/lista/", views.lista_clientes, name="lista_clientes"),
    path("admin/detalle/<int:id>/", views.detalle_cliente, name="detalle_cliente"),
    path("admin/editar/<int:id>/", views.editar_cliente, name="editar_cliente"),
]
