from django.urls import path

from apps.pedidos import views_pagos

app_name = "pagos"

urlpatterns = [
    path("", views_pagos.lista_pagos, name="lista_pagos"),
    path("registrar/<int:pedido_id>/", views_pagos.registrar_pago, name="registrar_pago"),
    path("<int:pk>/", views_pagos.detalle_pago, name="detalle_pago"),
    path("<int:pk>/revisar/", views_pagos.revisar_pago, name="revisar_pago"),
]
