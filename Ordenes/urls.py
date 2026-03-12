from django.urls import path
from . import views

urlpatterns = [

    path("", views.lista_ordenes, name="lista_ordenes"),

    path("crear/", views.crear_orden, name="crear_orden"),

]