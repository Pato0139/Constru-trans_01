from django.db import models 
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User


# -------------------------
# USUARIO
# -------------------------
class Usuario(models.Model):

    user = models.OneToOneField(User,  on_delete=models.CASCADE, related_name="usuario")

    ROLES = [
        ('admin', 'Administrador'),
        ('conductor', 'Conductor'),
        ('cliente', 'Cliente'),
        ('empleado', 'Empleado'),
    ]

    TIPOS_DOCUMENTO = [
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('PA', 'Pasaporte'),
        ('PEP', 'Permiso Especial de Permanencia'),
        ('PPT', 'Permiso por Protección Temporal'),
        ('NIT', 'Número de Identificación Tributaria'),
    ]

    ESTADO_USUARIO = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('suspendido', 'Suspendido'),
    ]

    rol = models.CharField(max_length=20, choices=ROLES)

    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPOS_DOCUMENTO
    )

    documento = models.CharField(max_length=20)

    estado = models.CharField(
        max_length=15,
        choices=ESTADO_USUARIO,
        default='activo'
    )

    def __str__(self):
        return self.nombre


# -------------------------
# VEHICULO
# -------------------------
class Vehiculo(models.Model):

    placa = models.CharField(max_length=10)
    tipo = models.CharField(max_length=50)
    capacidad = models.CharField(max_length=50)
    estado = models.CharField(max_length=50)

    def __str__(self):
        return self.placa


# -------------------------
# MATERIAL
# -------------------------
class Material(models.Model):
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50)
    descripcion = models.TextField()

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100000000)
        ]
    )

    stock = models.IntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100000)
        ]
    )

    def __str__(self):
        return self.nombre


class Orden(models.Model):
    cliente = models.ForeignKey('Usuario', on_delete=models.CASCADE)
    material = models.ForeignKey('Material', on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    direccion_origen = models.CharField(max_length=255)
    direccion_destino = models.CharField(max_length=255)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50, default='pendiente')

    def __str__(self):
        return f"Orden #{self.id}"