from django.db import models 
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.contrib.auth.models import User

# Validador para campos que solo deben contener números
numeric_validator = RegexValidator(
    regex=r'^\d+$',
    message="Este campo solo debe contener números."
)

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

    nombres = models.CharField(max_length=100, default="")
    apellidos = models.CharField(max_length=100, default="")
    telefono = models.CharField(
        max_length=20, 
        blank=True,
        validators=[numeric_validator]
    )
    foto_perfil = models.ImageField(upload_to='perfiles/', null=True, blank=True)

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPOS_DOCUMENTO
    )

    documento = models.CharField(
        max_length=20,
        validators=[numeric_validator]
    )

    estado = models.CharField(
        max_length=15,
        choices=ESTADO_USUARIO,
        default='activo'
    )

    def save(self, *args, **kwargs):
        if self.nombres:
            self.nombres = self.nombres.title()
        if self.apellidos:
            self.apellidos = self.apellidos.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

class Administrador(Usuario):
    class Meta:
        proxy = True
        verbose_name = 'Administrador'
        verbose_name_plural = 'Administradores'

class Conductor(Usuario):
    class Meta:
        proxy = True
        verbose_name = 'Conductor'
        verbose_name_plural = 'Conductores'

class Cliente(Usuario):
    class Meta:
        proxy = True
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'



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
    activo = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if self.nombre:
            self.nombre = self.nombre.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

# -------------------------
# STOCK MATERIAL
# -------------------------
class StockMaterial(models.Model):
    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name="stock")
    cantidad_actual = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )
    cantidad_minima = models.IntegerField(
        default=10,
        validators=[MinValueValidator(0)]
    )
    ubicacion = models.CharField(max_length=100, default="Bodega Principal")
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stock de {self.material.nombre}: {self.cantidad_actual}"

    class Meta:
        verbose_name = "Stock de Material"
        verbose_name_plural = "Stocks de Materiales"
