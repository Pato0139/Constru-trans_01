from django.urls import path
from . import views

app_name = 'ordenes'

urlpatterns = [
    path("lista/", views.lista_pedidos_admin, name="lista_pedidos_admin"),
    path("detalle/<int:id>/", views.ver_pedido_admin, name="ver_pedido_admin"),
    path("entregas/crear/<int:orden_id>/", views.crear_entrega, name="crear_entrega"),
    path('editar/<int:id>/', views.editar_orden, name="editar_orden"),
    path('eliminar/<int:id>/', views.eliminar_orden, name='eliminar_orden'),
    path('factura/<int:id>/', views.descargar_factura, name='descargar_factura'),
    path('api/total/<int:id>/', views.api_total_orden, name='api_total_orden'),
    # HU-29 CT-299 — Agregar y eliminar materiales del pedido
    path('<int:id>/materiales/', views.agregar_material_pedido, name='agregar_material_pedido'),
    path('<int:id>/materiales/<int:detalle_id>/eliminar/', views.eliminar_material_pedido, name='eliminar_material_pedido'),
]