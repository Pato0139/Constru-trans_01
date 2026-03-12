from django.db import models
from django.contrib.auth.models import User


# -------------------------
# USUARIO
# -------------------------
class Usuario(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE)

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
    telefono = models.CharField(max_length=20)

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

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()

    def __str__(self):
        return self.nombre