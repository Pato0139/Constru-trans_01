from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    path("", views.lista_pagos, name="lista_pagos"),
    path("<int:pk>/aprobar/", views.aprobar_pago, name="aprobar_pago"),
    path("<int:pk>/rechazar/", views.rechazar_pago, name="rechazar_pago"),
]
