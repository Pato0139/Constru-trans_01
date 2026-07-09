from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    path("historial/", views.lista_pagos, name="lista_pagos"),
    path("gestion/", views.gestion_pagos, name="gestion_pagos"),
    path("prototipo/", views.prototype_home, name="prototype_home"),
    path("prototipo/pedido/", views.prototype_order_form, name="prototype_order_form"),
    path("prototipo/pago/<str:order_id>/", views.prototype_payment_method, name="prototype_payment_method"),
    path("prototipo/mis-pedidos/", views.prototype_customer_orders, name="prototype_customer_orders"),
    path("prototipo/pedido/<str:order_id>/detalle/", views.prototype_order_detail, name="prototype_order_detail"),
    path("prototipo/gestion-pagos/", views.prototype_admin_orders, name="prototype_admin_orders"),
    path("prototipo/conductor/", views.prototype_conductor, name="prototype_conductor"),
    path("prototipo/rol/<str:role>/", views.prototype_switch_role, name="prototype_switch_role"),
]
