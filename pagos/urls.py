from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    path("", views.lista_pagos, name="lista_pagos"),
    path("registrar/<int:pedido_id>/", views.registrar_pago, name="registrar_pago"),
    path("<int:pk>/", views.detalle_pago, name="detalle_pago"),
    path("<int:pk>/revisar/", views.revisar_pago, name="revisar_pago"),
]
