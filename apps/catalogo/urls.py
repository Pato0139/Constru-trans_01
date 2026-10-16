from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("materiales/", views.materiales_lista, name="materiales_lista"),
    path("materiales/crear/", views.crear_material, name="crear_material"),
    path("materiales/editar/<int:id>/", views.editar_material, name="editar_material"),
    path("materiales/estado/<int:id>/", views.cambiar_estado_material, name="cambiar_estado_material"),
    path("materiales/eliminar/<int:id>/", views.eliminar_material, name="eliminar_material"),
    path("stock/", views.stock_lista, name="stock_lista"),
    path("stock/editar/<int:id>/", views.editar_stock, name="editar_stock"),
    path("movimientos/", views.movimientos_lista, name="movimientos_lista"),
    path("entrada/", views.registrar_entrada, name="registrar_entrada"),
    path("tipos/", views.tipos_material_lista, name="tipos_material_lista"),
    path("tipos/crear/", views.crear_tipo_material, name="crear_tipo_material"),
    path("tipos/editar/<str:codigo>/", views.editar_tipo_material, name="editar_tipo_material"),
    path("tipos/estado/<str:codigo>/", views.cambiar_estado_tipo, name="cambiar_estado_tipo"),
    path("tipos/eliminar/<str:codigo>/", views.eliminar_tipo_material, name="eliminar_tipo_material"),
    path("unidades/", views.unidades_medida_lista, name="unidades_medida_lista"),
    path("unidades/crear/", views.crear_unidad_medida, name="crear_unidad_medida"),
    path("unidades/editar/<int:id>/", views.editar_unidad_medida, name="editar_unidad_medida"),
    path("unidades/estado/<int:id>/", views.cambiar_estado_unidad_medida, name="cambiar_estado_unidad_medida"),
    path("unidades/eliminar/<int:id>/", views.eliminar_unidad_medida, name="eliminar_unidad_medida"),
    path("marcas/", views.marcas_lista, name="marcas_lista"),
    path("marcas/crear/", views.crear_marca, name="crear_marca"),
    path("marcas/editar/<int:id>/", views.editar_marca, name="editar_marca"),
    path("marcas/eliminar/<int:id>/", views.eliminar_marca, name="eliminar_marca"),
    path("marcas/estado/<int:id>/", views.cambiar_estado_marca, name="cambiar_estado_marca"),
    path("api/materiales/", views.api_materiales, name="api_materiales"),
    path("api/materiales/listado/", views.api_materiales_listado, name="api_materiales_listado"),
]
