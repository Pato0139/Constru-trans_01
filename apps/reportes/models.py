from django.db import models

from apps.usuarios.models import Usuario


# =====================================================================
# REPORTE  (MER: #numero_reporte *tipo *fecha_generada *estado
#           *descripcion *id_usuario)
# =====================================================================
class Reporte(models.Model):
    TIPOS = [
        ("inventario", "Inventario"),
        ("ventas", "Ventas"),
        ("compras", "Compras"),
        ("entregas", "Entregas"),
        ("financiero", "Financiero"),
    ]
    ESTADOS = [
        ("generado", "Generado"),
        ("archivado", "Archivado"),
        ("eliminado", "Eliminado"),
    ]

    numero_reporte = models.CharField(max_length=20, primary_key=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    fecha_generada = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default="generado")
    descripcion = models.TextField(blank=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)

    # Fuera del MER pero útil — NO se toca
    archivo_pdf = models.FileField(upload_to="reportes/", null=True, blank=True)

    class Meta:
        ordering = ["-fecha_generada"]
        db_table = "reporte"

    def __str__(self):
        return f"Reporte {self.numero_reporte}"


# =====================================================================
# HISTORIAL_REPORTES  (MER: #codigo_historia *fecha_reporte
#                     descripcion *numero_reporte)
# =====================================================================
class HistorialReporte(models.Model):
    codigo_historia = models.CharField(max_length=20, primary_key=True)
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name="historial")
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()

    class Meta:
        ordering = ["-fecha_reporte"]
        db_table = "historial_reporte"

    def __str__(self):
        return f"Historial {self.codigo_historia}"
