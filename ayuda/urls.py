from django.urls import path
from . import views


app_name = "ayuda"

urlpatterns = [
    path("", views.index_ayuda, name="index"),
    path("guias/", views.lista_guias, name="lista_guias"),
    path("guias/categoria/<int:categoria_id>/", views.lista_guias, name="lista_guias_categoria"),
    path("guias/<int:guia_id>/", views.detalle_guia, name="detalle_guia"),
    path("sugerencias/crear/", views.crear_sugerencia, name="crear_sugerencia"),
    path("colores/", views.lista_colores, name="lista_colores"),
]
