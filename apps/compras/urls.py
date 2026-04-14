from django.urls import path
from . import views

app_name = 'compras'

urlpatterns = [
    path('proveedores/', views.lista_proveedores, name='lista_proveedores'),
    path('proveedores/crear/', views.crear_proveedor, name='crear_proveedor'),
    path('proveedores/editar/<int:id>/', views.editar_proveedor, name='editar_proveedor'),
    path('proveedores/contactar/<int:id>/', views.contactar_proveedor, name='contactar_proveedor'),
    path('proveedores/eliminar/<int:id>/', views.eliminar_proveedor, name='eliminar_proveedor'),
    path('proveedores/estado/<int:id>/', views.cambiar_estado_proveedor, name='cambiar_estado_proveedor'),
]
