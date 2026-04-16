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
    path('factura/<int:id>/<str:formato>/', views.descargar_factura, name='descargar_factura_formato'),
]
