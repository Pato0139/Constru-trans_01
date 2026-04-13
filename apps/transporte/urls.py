from django.urls import path
from . import views

app_name = 'transporte'

urlpatterns = [
    # Vehículos
    path("vehiculos/", views.lista_vehiculos, name="lista_vehiculos"),
    path("vehiculos/crear/", views.crear_vehiculo, name="crear_vehiculo"),
    path("vehiculos/editar/<int:id>/", views.editar_vehiculo, name="editar_vehiculo"),
    path("vehiculos/eliminar/<int:id>/", views.eliminar_vehiculo, name="eliminar_vehiculo"),

    # Entregas
    path("entregas/", views.lista_entregas, name="lista_entregas"),
    path("entregas/crear/", views.crear_entrega, name="crear_entrega"),
    path("entregas/<int:id>/editar/", views.editar_entrega, name="editar_entrega"),
    path("entregas/<int:id>/eliminar/", views.eliminar_entrega, name="eliminar_entrega"),
    path("entregas/<int:id>/estado/", views.actualizar_estado_entrega, name="actualizar_estado_entrega"),
]