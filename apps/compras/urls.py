from django.urls import path
from . import views

app_name = 'compras'

urlpatterns = [
    # Compras
    path('', views.lista_compras, name='lista_compras'),
    path('crear/', views.crear_compra, name='crear_compra'),
    path('detalle/<int:id>/', views.detalle_compra, name='detalle_compra'),
    path('editar/<int:id>/', views.editar_compra, name='editar_compra'),
    path('estado/<int:id>/', views.cambiar_estado_compra, name='cambiar_estado_compra'),

    # Proveedores
    path('proveedores/', views.lista_proveedores, name='lista_proveedores'),
    path('proveedores/crear/', views.crear_proveedor, name='crear_proveedor'),
    path('proveedores/editar/<int:id>/', views.editar_proveedor, name='editar_proveedor'),
    path('proveedores/contactar/<int:id>/', views.contactar_proveedor, name='contactar_proveedor'),
]
