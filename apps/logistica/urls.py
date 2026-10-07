from django.urls import path

from . import views

app_name = "logistica"

urlpatterns = [
    path("vehiculos/", views.lista_vehiculos, name="lista_vehiculos"),
    path("vehiculos/crear/", views.crear_vehiculo, name="crear_vehiculo"),
    path("vehiculos/editar/<int:id>/", views.editar_vehiculo, name="editar_vehiculo"),
    path("vehiculos/desactivar/<int:id>/", views.desactivar_vehiculo, name="desactivar_vehiculo"),
    path("vehiculos/disponibilidad/<int:id>/", views.cambiar_disponibilidad_vehiculo, name="cambiar_disponibilidad_vehiculo"),
    path("vehiculos/eliminar/<int:id>/", views.eliminar_vehiculo, name="eliminar_vehiculo"),
    path("novedades/crear/<int:entrega_id>/", views.crear_novedad, name="crear_novedad"),
    path("novedades/<int:novedad_id>/seguimiento/", views.agregar_seguimiento, name="agregar_seguimiento"),
    path("novedades/<int:seguimiento_id>/responder/", views.responder_seguimiento, name="responder_seguimiento"),
]
