from django.urls import path
from . import views
app_name = "novedades"
urlpatterns = [
    path("crear/<int:pedido_id>/",         views.crear_novedad,         name="crear"),
    path("<int:novedad_id>/seguimiento/",  views.agregar_seguimiento,   name="seguimiento"),
    path("<int:seguimiento_id>/responder/", views.responder_seguimiento, name="responder"),
]
