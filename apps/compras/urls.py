from django.urls import path

from . import views

app_name = "compras"

urlpatterns = [
    # Compras
    path("", views.lista_compras, name="lista_compras"),
    path("crear/", views.crear_compra, name="crear_compra"),
    path("detalle/<int:id>/", views.detalle_compra, name="detalle_compra"),
    path("editar/<int:id>/", views.editar_compra, name="editar_compra"),
    path("estado/<int:id>/", views.cambiar_estado_compra, name="cambiar_estado_compra"),
    # Proveedores
    path("proveedores/", views.lista_proveedores, name="lista_proveedores"),
    path("proveedores/crear/", views.crear_proveedor, name="crear_proveedor"),
    path(
        "proveedores/editar/<int:codigo_proveedor>/",
        views.editar_proveedor,
        name="editar_proveedor",
    ),
    path(
        "proveedores/contactar/<int:codigo_proveedor>/",
        views.contactar_proveedor,
        name="contactar_proveedor",
    ),
    path(
        "proveedores/estado/<int:codigo_proveedor>/",
        views.cambiar_estado_proveedor,
        name="cambiar_estado_proveedor",
    ),
    path(
        "proveedores/perfil/<int:codigo_proveedor>/",
        views.perfil_proveedor,
        name="perfil_proveedor",
    ),
    path(
        "proveedores/<int:codigo_proveedor>/materiales/",
        views.materiales_proveedor_json,
        name="materiales_proveedor_json",
    ),
]
