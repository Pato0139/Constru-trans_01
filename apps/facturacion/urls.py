from django.urls import path
from . import views

app_name = 'facturacion'

urlpatterns = [
    path('', views.lista_facturas, name='lista_facturas'),
    path('pagos/', views.registrar_pago, name='registrar_pago'),
]
