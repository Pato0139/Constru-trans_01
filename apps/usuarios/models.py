from django.db import models 
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.contrib.auth.models import User

# Validador para permitir solo números y espacios
numeric_and_space_validator = RegexValidator(
    regex=r'^[0-9\s]*$',
    message='Solo se admiten números y espacios.',
    code='invalid_numeric_space'
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
    telefono = models.CharField(max_length=20, blank=True, validators=[numeric_and_space_validator])
    foto_perfil = models.ImageField(upload_to='perfiles/', null=True, blank=True)

    tipo_documento = models.CharField(
        max_length=5,
        choices=TIPOS_DOCUMENTO
    )

    documento = models.CharField(max_length=20, validators=[numeric_and_space_validator])

    estado = models.CharField(
        max_length=15,
        choices=ESTADO_USUARIO,
        default='activo'
    )
    
    sincronizado = models.BooleanField(default=False, verbose_name="Sincronizado con Nube")

    class Meta:
        db_table = 'usuario'

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

    placa = models.CharField(max_length=10, unique=True)
    tipo = models.CharField(max_length=50)
    capacidad = models.CharField(max_length=50)
    
    ESTADOS_VEHICULO = [
        ('disponible', 'Disponible'),
        ('en_ruta', 'En Ruta'),
        ('mantenimiento', 'Mantenimiento'),
        ('alquilado', 'Alquilado'),
        ('comprado', 'Comprado'),
        ('desactivado', 'Desactivado'),
    ]
    
    TIPO_ADQUISICION = [
        ('propio', 'Propio (Comprado)'),
        ('alquilado', 'Alquilado'),
    ]

    tipo_adquisicion = models.CharField(
        max_length=20,
        choices=TIPO_ADQUISICION,
        default='propio',
        verbose_name="Tipo de Adquisición"
    )
    
    estado = models.CharField(
        max_length=20, 
        choices=ESTADOS_VEHICULO, 
        default='disponible'
    )
    
    sincronizado = models.BooleanField(default=False, help_text="Indica si el registro está sincronizado con la nube")

    conductor = models.OneToOneField(
        Usuario, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="vehiculo_asignado",
        limit_choices_to={'rol': 'conductor'}
    )

    class Meta:
        db_table = 'vehiculo'

    def __str__(self):
        return f"{self.placa} ({self.tipo})"


# -------------------------
# MATERIAL
# -------------------------
class Proveedor(models.Model):
    nombre_empresa = models.CharField(max_length=150)
    nit = models.CharField(max_length=20, unique=True, validators=[numeric_and_space_validator])
    contacto_nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, validators=[numeric_and_space_validator])
    email = models.EmailField()
    direccion = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100, help_text="Ej: Materiales de Construcción, Repuestos, etc.")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    sincronizado = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.nombre_empresa} ({self.nit})"

    class Meta:
        verbose_name_plural = "Proveedores"
        db_table = 'proveedor'

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
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'material'

    @property
    def stock(self):
        """Mantiene compatibilidad con lecturas de material.stock"""
        try:
            return self.stock_info.cantidad
        except Stock.DoesNotExist:
            return 0

    def __str__(self):
        return self.nombre

class Stock(models.Model):
    material = models.OneToOneField(Material, on_delete=models.CASCADE, related_name='stock_info')
    cantidad = models.IntegerField(
        default=0,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100000)
        ]
    )
    ubicacion = models.CharField(max_length=100, default='Bodega Principal')
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock'

    def __str__(self):
        return f"Stock de {self.material.nombre}: {self.cantidad}"

class Notificacion(models.Model):
    TIPOS = [
        ('info', 'Información'),
        ('success', 'Éxito'),
        ('warning', 'Advertencia'),
        ('danger', 'Error'),
    ]
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones')
    titulo = models.CharField(max_length=100, default="Nueva notificación")
    mensaje = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPOS, default='info')
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['-fecha']
        db_table = 'notificacion'

    def __str__(self):
        return f"Notificación para {self.usuario}: {self.mensaje[:20]}..."
