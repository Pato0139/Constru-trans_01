from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path("admin/", views.reportes_admin, name="reportes_admin"),
    path("pedidos/", views.reportes_pedidos, name="reportes_pedidos"),
    path("ventas/", views.reportes_ventas, name="reportes_ventas"),
    path("exportar/<str:tipo>/", views.exportar_reporte_pdf, name="exportar_reporte_pdf"),
    path("exportar/<str:tipo>/<str:formato>/", views.exportar_reporte, name="exportar_reporte"),
]
