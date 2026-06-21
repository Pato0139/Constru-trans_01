from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    path("historial/", views.lista_pagos, name="lista_pagos"),
    path("<int:id_pago>/", views.detalle_pago, name="detalle_pago"),
    path("factura/<int:id_factura>/pagar/", views.procesar_pago, name="procesar_pago"),
    path(
        "<int:id_pago>/actualizar-estado/",
        views.actualizar_estado_pago,
        name="actualizar_estado_pago",
    ),
]
