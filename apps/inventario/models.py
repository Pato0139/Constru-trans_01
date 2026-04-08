from django.db import models


class Material(models.Model):
    TIPO_CHOICES = [
        ('Cemento', 'Cemento'),
        ('Arena', 'Arena'),
        ('Grava', 'Grava'),
        ('Ladrillo', 'Ladrillo'),
        ('Herramientas', 'Herramientas'),
        ('Otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=200, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    tipo = models.CharField(
        max_length=50,
        choices=TIPO_CHOICES,
        default='Otro',
        verbose_name='Tipo'
    )
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Precio (COP)'
    )
    stock = models.PositiveIntegerField(default=0, verbose_name='Stock disponible')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Material'
        verbose_name_plural = 'Materiales'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} - Stock: {self.stock}"