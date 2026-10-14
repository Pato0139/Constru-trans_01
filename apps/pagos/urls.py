from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    # Pago asociado directamente a Pedido (flujo legacy)
    path("", views.lista_pagos, name="lista_pagos"),
    path("registrar/<int:pedido_id>/", views.registrar_pago_pedido, name="registrar_pago_pedido"),
    path("<int:pk>/", views.detalle_pago, name="detalle_pago"),
    path("<int:pk>/revisar/", views.revisar_pago_pedido, name="revisar_pago_pedido"),

    # Facturación y pagos consolidados
    path("facturas/", views.lista_facturas, name="lista_facturas"),
    path("facturas/<int:pk>/", views.detalle_factura, name="detalle_factura"),
    path("facturas/<int:pk>/pago/", views.registrar_pago, name="registrar_pago"),
    path("facturas/<int:pk>/pago/<int:pago_id>/revisar/", views.revisar_pago, name="revisar_pago"),
    path("facturas/<int:pk>/pdf/", views.descargar_pdf, name="descargar_factura"),
    path("pedido/<int:pedido_id>/pdf/", views.descargar_factura_pedido, name="descargar_factura_pedido"),

    path("gestion/", views.gestion_pagos, name="gestion_pagos"),
    path("historial/", views.historial_pagos, name="historial_pagos"),

    path("mis-facturas/", views.mis_facturas, name="mis_facturas"),
    path("mis-pagos/", views.mis_pagos, name="mis_pagos"),
]
