from django.urls import path

from core import views_auditoria

app_name = "auditoria"

urlpatterns = [
    path("lista/", views_auditoria.lista_historial, name="lista_historial"),
]
