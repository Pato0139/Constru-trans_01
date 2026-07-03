from django.db import models
from django.utils import timezone
from usuarios.models import Usuario


class CategoriaAyuda(models.Model):
    """Categorías para organizar las guías y ayudas."""
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "categoria_ayuda"
        verbose_name_plural = "Categorías de Ayuda"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class GuiaEdicion(models.Model):
    """Guías paso a paso para editar diferentes elementos del sistema."""
    titulo = models.CharField(max_length=200)
    categoria = models.ForeignKey(CategoriaAyuda, on_delete=models.CASCADE, related_name="guias")
    contenido = models.TextField()
    orden = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    es_favorito = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "guia_edicion"
        verbose_name = "Guía de Edición"
        verbose_name_plural = "Guías de Edición"
        ordering = ["categoria", "orden", "titulo"]

    def __str__(self):
        return self.titulo


class PasoGuia(models.Model):
    """Pasos individuales dentro de una guía de edición."""
    guia = models.ForeignKey(GuiaEdicion, on_delete=models.CASCADE, related_name="pasos")
    numero_paso = models.PositiveIntegerField()
    titulo_paso = models.CharField(max_length=200)
    descripcion = models.TextField()
    imagen = models.ImageField(upload_to="ayuda/pasos/", null=True, blank=True)
    url_referencia = models.URLField(null=True, blank=True)

    class Meta:
        db_table = "paso_guia"
        ordering = ["guia", "numero_paso"]

    def __str__(self):
        return f"{self.guia.titulo} - Paso {self.numero_paso}: {self.titulo_paso}"


class SugerenciaRecomendacion(models.Model):
    """Sugerencias y recomendaciones de los usuarios."""
    TIPOS = [
        ("sugerencia", "Sugerencia"),
        ("recomendacion", "Recomendación"),
        ("bug", "Reporte de Error"),
        ("mejora", "Mejora"),
    ]

    ESTADOS = [
        ("nuevo", "Nuevo"),
        ("en_revision", "En Revisión"),
        ("implementado", "Implementado"),
        ("rechazado", "Rechazado"),
    ]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="sugerencias")
    tipo = models.CharField(max_length=20, choices=TIPOS)
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default="nuevo")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sugerencia_recomendacion"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.tipo}: {self.titulo}"


class ManualUsuario(models.Model):
    """Manual de usuario completo."""
    titulo = models.CharField(max_length=200)
    version = models.CharField(max_length=50)
    archivo = models.FileField(upload_to="manuales/")
    fecha_publicacion = models.DateField(default=timezone.now)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "manual_usuario"
        verbose_name = "Manual de Usuario"
        verbose_name_plural = "Manuales de Usuario"

    def __str__(self):
        return f"{self.titulo} v{self.version}"


class ColorSistema(models.Model):
    """Colores del sistema para la paleta visual."""
    nombre = models.CharField(max_length=100)
    codigo_hex = models.CharField(max_length=7)  # Ej: #FF0000
    descripcion = models.TextField(blank=True)
    uso = models.CharField(max_length=200)  # Para qué se usa este color
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "color_sistema"
        verbose_name = "Color del Sistema"
        verbose_name_plural = "Colores del Sistema"

    def __str__(self):
        return f"{self.nombre} ({self.codigo_hex})"
