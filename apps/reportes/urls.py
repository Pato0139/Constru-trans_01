from django.urls import path
from . import views

app_name = 'reportes'

urlpatterns = [
    path("admin/", views.reportes_admin, name="reportes_admin"),
    path("exportar/<str:tipo>/", views.exportar_reporte_pdf, name="exportar_reporte_pdf"),
    path("exportar/excel/<str:tipo>/", views.exportar_reporte_excel, name="exportar_reporte_excel"),
    path("exportar/xml/<str:tipo>/", views.exportar_reporte_xml, name="exportar_reporte_xml"),
]
