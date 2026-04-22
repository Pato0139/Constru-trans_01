from django.urls import path
from . import views

app_name = 'compras'

urlpatterns = [
    # ── Proveedores ───────────────────────────────────────────────
    path('proveedores/',                          views.lista_proveedores,       name='lista_proveedores'),
    path('proveedores/crear/',                    views.crear_proveedor,         name='crear_proveedor'),
    path('proveedores/editar/<int:id>/',          views.editar_proveedor,        name='editar_proveedor'),

    # ── HU-23: Órdenes de compra ──────────────────────────────────
    path('ordenes/',                              views.lista_ordenes_compra,    name='lista_ordenes'),
    path('ordenes/nueva/',                        views.registrar_orden_compra,  name='registrar_orden'),
    path('ordenes/<int:pk>/',                     views.detalle_orden_compra,    name='detalle_orden'),
    path('ordenes/<int:pk>/editar/',              views.editar_orden_compra,     name='editar_orden'),
    path('ordenes/<int:pk>/estado/<str:estado>/', views.cambiar_estado_orden,    name='cambiar_estado'),

    # ── HU-24: Registrar detalle de orden ─────────────────────────
    path('ordenes/<int:pk>/detalle/registrar/',   views.registrar_detalle_orden, name='registrar_detalle'),
]