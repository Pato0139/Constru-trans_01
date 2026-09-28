from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    path("", views.lista_pagos, name="lista_pagos"),
<<<<<<< HEAD
    path("<int:pk>/aprobar/", views.aprobar_pago, name="aprobar_pago"),
    path("<int:pk>/rechazar/", views.rechazar_pago, name="rechazar_pago"),
=======
    path("registrar/<int:pedido_id>/", views.registrar_pago, name="registrar_pago"),
    path("<int:pk>/", views.detalle_pago, name="detalle_pago"),
    path("<int:pk>/revisar/", views.revisar_pago, name="revisar_pago"),
>>>>>>> 49984237c7825998944fb40ba7acb96be2e3d525
]
