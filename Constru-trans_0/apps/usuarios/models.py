
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.contrib.auth.models import User

numeric_and_space_validator = RegexValidator(
    regex=r'^[0-9\s]*$',
    message='Solo se admiten números y espacios.',
    code='invalid_numeric_space'
)


# =====================================================================
# USUARIO  (MER: #id_usuario *nombres *apellidos *telefono *documento *contraseña)
# Un usuario tiene UN solo rol (VARCHAR).
# =====================================================================
class Usuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="usuario")

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
    ROLES = [
        ('admin', 'Admin'),
        ('cliente', 'Cliente'),
        ('conductor', 'Conductor'),
        ('empleado', 'Empleado'),
    ]

    # Campos del MER - match remote database schema EXACTLY
    nombres = models.CharField(max_length=200)
    apellidos = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    documento = models.CharField(max_length=20, validators=[numeric_and_space_validator])
    
    # Rol is a VARCHAR column, not a foreign key!
    rol = models.CharField(max_length=50, choices=ROLES)

    # Fuera del MER pero útil — NO se toca
    tipo_documento = models.CharField(max_length=5, choices=TIPOS_DOCUMENTO)
    estado = models.CharField(max_length=15, choices=ESTADO_USUARIO, default='activo')
    foto_perfil = models.ImageField(upload_to='perfiles/', null=True, blank=True)
    sincronizado = models.BooleanField(default=False)

    @property
    def contraseña(self):
        return self.user.password

    @property
    def iniciales(self):
        partes = self.nombres.split()
        return "".join([p[0].upper() for p in partes[:2]]) or "?"

    @property
    def color_avatar(self):
        colores = ["#3B82F6", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6",
                   "#EC4899", "#06B6D4", "#84CC16", "#F97316", "#6366F1"]
        return colores[self.id % len(colores)] if self.id else colores[0]

    @property
    def es_admin(self):
        return self.rol == 'admin'

    @property
    def es_conductor(self):
        return self.rol == 'conductor'

    @property
    def es_cliente(self):
        return self.rol == 'cliente'

    @property
    def es_empleado(self):
        return self.rol == 'empleado'

    @property
    def nombre(self):
        return self.nombres

    class Meta:
        db_table = 'usuario'

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.rol})"


# =====================================================================
# EPS  (MER: #codigo_EPS *numero_seguro *ciudad *direccion *telefono *correo)
# =====================================================================
class EPS(models.Model):
    codigo_eps = models.CharField(max_length=20, primary_key=True)
    numero_seguro = models.CharField(max_length=50)
    ciudad = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField()

    class Meta:
        db_table = 'eps'
        verbose_name_plural = "EPS"

    def __str__(self):
        return f"EPS {self.codigo_eps}"


# =====================================================================
# CONDUCTOR  (MER: #id_usuario(FK)(PK) *numero_licencia *categoria_licencia ...)
# Antes: PerfilConductor
# =====================================================================
class Conductor(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE,
                                   primary_key=True, related_name='perfil_conductor')
    numero_licencia = models.CharField(max_length=50, unique=True)
    categoria_licencia = models.CharField(max_length=10)
    fecha_vencimiento_licencia = models.DateField()
    telefono_empresarial = models.CharField(max_length=20, blank=True)

    ESTADO_CONDUCTOR = [('activo', 'Activo'), ('inactivo', 'Inactivo')]
    estado = models.CharField(max_length=15, choices=ESTADO_CONDUCTOR, default='activo')
    fecha_ingreso = models.DateField(null=True, blank=True)
    eps = models.ForeignKey(EPS, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'conductor'

    def __str__(self):
        return f"Conductor: {self.usuario.nombres}"


# =====================================================================
# VEHICULO  (MER: #id_vehiculo *placa *marca *modelo *tipo_vehiculo
#           *capacidad_carga *estado *fecha_registro)
# =====================================================================
class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True)
    placa = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    tipo_vehiculo = models.CharField(max_length=50)
    capacidad_carga = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    ESTADOS_VEHICULO = [
        ('disponible', 'Disponible'),
        ('en_ruta', 'En Ruta'),
        ('mantenimiento', 'Mantenimiento'),
        ('desactivado', 'Desactivado'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS_VEHICULO, default='disponible')

    # Fuera del MER pero útil — NO se toca
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'vehiculo'

    def __str__(self):
        return f"{self.placa} ({self.marca} {self.modelo})"


# =====================================================================
# CONDUCTOR_VEHICULO  (MER: tabla puente N:M)
# =====================================================================
class ConductorVehiculo(models.Model):
    conductor = models.ForeignKey(Conductor, on_delete=models.CASCADE,
                                  related_name='asignaciones_vehiculo')
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE,
                                 related_name='asignaciones_conductor')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'conductor_vehiculo'
        unique_together = ('conductor', 'vehiculo', 'fecha_asignacion')
        ordering = ['-fecha_asignacion']

    def __str__(self):
        return f"{self.conductor} - {self.vehiculo.placa}"


# =====================================================================
# CATALOGO  (MER: #codigo_catalogo *nombre_empresa)
# =====================================================================
class Catalogo(models.Model):
    codigo_catalogo = models.CharField(max_length=20, primary_key=True)
    nombre_empresa = models.CharField(max_length=150)

    class Meta:
        db_table = 'catalogo'

    def __str__(self):
        return self.nombre_empresa


# =====================================================================
# PROVEEDOR  (MER: #codigo_proveedor *telefono *correo *descripcion)
# =====================================================================
class Proveedor(models.Model):
    codigo_proveedor = models.AutoField(primary_key=True)
    nombre_empresa = models.CharField(max_length=150)
    nit = models.CharField(max_length=20, unique=True, validators=[numeric_and_space_validator])
    telefono = models.CharField(max_length=20, validators=[numeric_and_space_validator])
    correo = models.EmailField()
    descripcion = models.TextField(blank=True)
    # Fuera del MER — NO se toca
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'proveedor'
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return f"{self.nombre_empresa} ({self.nit})"


# =====================================================================
# MATERIAL_CONSTRUCCION  (MER: #cod_material *nombre *unidad_medida ...)
# Antes: Material
# =====================================================================
class MaterialConstruccion(models.Model):
    cod_material = models.AutoField(primary_key=True)
    catalogo = models.ForeignKey(Catalogo, on_delete=models.SET_NULL,
                                 null=True, blank=True, related_name='materiales')
    nombre = models.CharField(max_length=100)
    unidad_medida = models.CharField(max_length=20)
    descripcion = models.TextField()
    precio_referencia = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100000000)]
    )
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = 'material_construccion'
        verbose_name = "Material de Construcción"
        verbose_name_plural = "Materiales de Construcción"

    @property
    def stock(self):
        try:
            return self.stock_info.cantidad_actual
        except Stock.DoesNotExist:
            return 0

    @property
    def precio(self):
        return self.precio_referencia

    def __str__(self):
        return self.nombre


# =====================================================================
# STOCK  (MER: #id_material(PK)(FK) - cantidad_actual - stock_minimo - fecha_actualizacion)
# =====================================================================
class Stock(models.Model):
    material = models.OneToOneField(MaterialConstruccion, on_delete=models.CASCADE,
                                    primary_key=True, related_name='stock_info')
    cantidad_actual = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100000)]
    )
    stock_minimo = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock'

    def __str__(self):
        return f"Stock {self.material.nombre}: {self.cantidad_actual}"


# =====================================================================
# METODO_PAGO  (MER: #codigo_metodo_pago *metodo)
# =====================================================================
class MetodoPago(models.Model):
    codigo_metodo_pago = models.CharField(max_length=20, primary_key=True)
    metodo = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = 'metodo_pago'
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"

    def __str__(self):
        return self.metodo


# =====================================================================
# NOTIFICACION  (FUERA del MER — NO se toca)
# =====================================================================
class Notificacion(models.Model):
    TIPOS = [('info', 'Información'), ('success', 'Éxito'),
             ('warning', 'Advertencia'), ('danger', 'Error')]
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
        return f"Notif {self.usuario}: {self.mensaje[:20]}..."


Material = MaterialConstruccion
