from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path("materiales/", views.materiales_lista, name="materiales_lista"),
    path("materiales/crear/", views.crear_material, name="crear_material"),
    path("materiales/editar/<int:id>/", views.editar_material, name="editar_material"),
    path("materiales/eliminar/<int:id>/", views.eliminar_material, name="eliminar_material"),

    # Stock
    path("stock/", views.stock_lista, name="stock_lista"),
    path("stock/editar/<int:id>/", views.editar_stock, name="editar_stock"),
    path("movimientos/", views.movimientos_lista, name="movimientos_lista"),
    path("entrada/", views.registrar_entrada, name="registrar_entrada"),

    path("api/materiales/", views.api_materiales, name="api_materiales"),
]
