from django.urls import path
from . import views

app_name = 'gestion_pedidos'

urlpatterns = [
    path('crear/', views.crear_pedido, name='crear'),
    path('', views.listar_pedidos, name='lista'),
    path('<int:pk>/', views.detalle_pedido, name='detalle'),
    path('<int:pk>/aprobar/', views.aprobar_pedido, name='aprobar'),
    path('<int:pk>/cancelar/', views.cancelar_pedido, name='cancelar'),
]
