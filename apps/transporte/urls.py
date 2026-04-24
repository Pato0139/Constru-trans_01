from django.urls import path
from . import views

app_name = 'transporte'

urlpatterns = [
    path("vehiculos/", views.lista_vehiculos, name="lista_vehiculos"),
    path("vehiculos/crear/", views.crear_vehiculo, name="crear_vehiculo"),
    path("vehiculos/editar/<int:id>/", views.editar_vehiculo, name="editar_vehiculo"),
    path("vehiculos/desactivar/<int:id>/", views.desactivar_vehiculo, name="desactivar_vehiculo"),
    path("vehiculos/eliminar/<int:id>/", views.eliminar_vehiculo, name="eliminar_vehiculo"),
]
