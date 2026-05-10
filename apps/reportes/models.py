from django.db import models
from apps.usuarios.models import Usuario


class Reporte(models.Model):
    TIPOS = [
        ('inventario', 'Inventario'),
        ('ventas', 'Ventas'),
        ('compras', 'Compras'),
        ('entregas', 'Entregas'),
        ('financiero', 'Financiero'),
    ]
    ESTADOS = [
        ('generado', 'Generado'),
        ('archivado', 'Archivado'),
        ('eliminado', 'Eliminado'),
    ]

    numero_reporte = models.CharField(max_length=20, unique=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    fecha_generada = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='generado')
    descripcion = models.TextField(blank=True)
    generado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    archivo_pdf = models.FileField(upload_to='reportes/', null=True, blank=True)

    class Meta:
        db_table = 'reporte'
        ordering = ['-fecha_generada']

    def __str__(self):
        return f"Reporte {self.numero_reporte} - {self.get_tipo_display()}"


class HistorialReporte(models.Model):
    reporte = models.ForeignKey(Reporte, on_delete=models.CASCADE, related_name='historial')
    codigo_historia = models.CharField(max_length=20, unique=True)
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField()

    class Meta:
        db_table = 'historial_reporte'
        ordering = ['-fecha_reporte']

    def __str__(self):
        return f"Historial {self.codigo_historia} - {self.reporte.numero_reporte}"
