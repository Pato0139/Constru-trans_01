from django.urls import path

from apps.auditoria import views as views_auditoria

app_name = "auditoria"

urlpatterns = [
    path("lista/", views_auditoria.lista_historial, name="lista_historial"),
]
