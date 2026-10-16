from django.urls import path

from apps.reportes import views as views_reportes

app_name = "reportes"

urlpatterns = [
    path("admin/", views_reportes.reportes_admin, name="reportes_admin"),
    path("exportar/<str:tipo>/", views_reportes.exportar_reporte_pdf, name="exportar_reporte_pdf"),
    path(
        "exportar/excel/<str:tipo>/",
        views_reportes.exportar_reporte_excel,
        name="exportar_reporte_excel",
    ),
    path(
        "exportar/xml/<str:tipo>/", views_reportes.exportar_reporte_xml, name="exportar_reporte_xml"
    ),
]
