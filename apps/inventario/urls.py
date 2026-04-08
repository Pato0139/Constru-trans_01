from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path("materiales/", views.materiales_lista, name="materiales_lista"),
    path("materiales/api/", views.api_materiales, name="api_materiales"),
    path("materiales/crear/", views.crear_material, name="crear_material"),
    path("materiales/editar/<int:id>/", views.editar_material, name="editar_material"),
    path("materiales/eliminar/<int:id>/", views.eliminar_material, name="eliminar_material"),
]