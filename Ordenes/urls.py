from django.urls import path
from . import views

urlpatterns = [

    path("", views.lista_ordenes, name="lista_ordenes"),

    path("crear/", views.crear_orden, name="crear_orden"),
    path("entregas/crear/<int:orden_id>/",views.crear_entrega, name="crear_entrega"),
    path('editar/<int:orden_id>/', views.editar_orden, name="editar_orden"),
    path('eliminar/<int:orden_id>/', views.eliminar_orden, name='eliminar_orden')

]