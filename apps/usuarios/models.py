from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

numeric_and_space_validator = RegexValidator(
    regex=r"^[0-9\s]*$", message="Solo se admiten números y espacios.", code="invalid_numeric_space"
)


# =====================================================================
# USUARIO  (MER: #id_usuario *nombres *apellidos *telefono *documento *contraseña)
# Un usuario tiene UN solo rol (VARCHAR).
# =====================================================================
class Usuario(AbstractUser):
    TIPOS_DOCUMENTO = [
        ("CC", "Cédula de Ciudadanía"),
        ("CE", "Cédula de Extranjería"),
        ("PA", "Pasaporte"),
        ("PEP", "Permiso Especial de Permanencia"),
        ("PPT", "Permiso por Protección Temporal"),
        ("NIT", "Número de Identificación Tributaria"),
    ]
    ESTADO_USUARIO = [
        ("activo", "Activo"),
        ("inactivo", "Inactivo"),
        ("suspendido", "Suspendido"),
    ]
    ROLES = [
        ("admin", "Admin"),
        ("cliente", "Cliente"),
        ("conductor", "Conductor"),
        ("empleado", "Empleado"),
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
    estado = models.CharField(max_length=15, choices=ESTADO_USUARIO, default="activo")
    foto_perfil = models.ImageField(upload_to="perfiles/", null=True, blank=True)
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = "usuario"

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.rol})"

    @property
    def contraseña(self):
        return self.password

    @property
    def usuario(self):
        return self

    @property
    def user(self):
        return self

    @property
    def iniciales(self):
        partes = self.nombres.split()
        return "".join([p[0].upper() for p in partes[:2]]) or "?"

    @property
    def color_avatar(self):
        colores = [
            "#3B82F6",
            "#EF4444",
            "#10B981",
            "#F59E0B",
            "#8B5CF6",
            "#EC4899",
            "#06B6D4",
            "#84CC16",
            "#F97316",
            "#6366F1",
        ]
        return colores[self.id % len(colores)] if self.id else colores[0]

    @property
    def es_admin(self):
        return self.rol == "admin"

    @property
    def es_conductor(self):
        return self.rol == "conductor"

    @property
    def es_cliente(self):
        return self.rol == "cliente"

    @property
    def es_empleado(self):
        return self.rol == "empleado"

    @property
    def nombre(self):
        return self.nombres


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
        db_table = "eps"
        verbose_name_plural = "EPS"

    def __str__(self):
        return f"EPS {self.codigo_eps}"


# =====================================================================
# CONDUCTOR  (MER: #id_usuario(FK)(PK) *numero_licencia *categoria_licencia ...)
# Antes: PerfilConductor
# =====================================================================
class Conductor(models.Model):
    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, primary_key=True, related_name="perfil_conductor"
    )
    numero_licencia = models.CharField(max_length=50, unique=True)
    categoria_licencia = models.CharField(max_length=10)
    fecha_vencimiento_licencia = models.DateField()
    telefono_empresarial = models.CharField(max_length=20, blank=True)

    ESTADO_CONDUCTOR = [("activo", "Activo"), ("inactivo", "Inactivo")]
    estado = models.CharField(max_length=15, choices=ESTADO_CONDUCTOR, default="activo")
    fecha_ingreso = models.DateField(null=True, blank=True)
    eps = models.ForeignKey(EPS, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "conductor"

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
        ("disponible", "Disponible"),
        ("en_ruta", "En Ruta"),
        ("mantenimiento", "Mantenimiento"),
        ("desactivado", "Desactivado"),
    ]
    estado = models.CharField(max_length=20, choices=ESTADOS_VEHICULO, default="disponible")

    # Fuera del MER pero útil — NO se toca
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = "vehiculo"

    def __str__(self):
        return f"{self.placa} ({self.marca} {self.modelo})"

    @property
    def id(self):
        return self.id_vehiculo

    @property
    def tipo(self):
        return self.tipo_vehiculo

    @property
    def capacidad(self):
        return self.capacidad_carga

    @property
    def conductor_actual(self):
        asignacion = (
            self.asignaciones_conductor.select_related("conductor__usuario")
            .order_by("-fecha_asignacion")
            .first()
        )
        return asignacion.conductor.usuario if asignacion else None


# =====================================================================
# CONDUCTOR_VEHICULO  (MER: tabla puente N:M)
# =====================================================================
class ConductorVehiculo(models.Model):
    conductor = models.ForeignKey(
        Conductor, on_delete=models.CASCADE, related_name="asignaciones_vehiculo"
    )
    vehiculo = models.ForeignKey(
        Vehiculo, on_delete=models.CASCADE, related_name="asignaciones_conductor"
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "conductor_vehiculo"
        unique_together = ("conductor", "vehiculo", "fecha_asignacion")
        ordering = ["-fecha_asignacion"]

    def __str__(self):
        return f"{self.conductor} - {self.vehiculo.placa}"


# =====================================================================
# CATALOGO  (MER: #codigo_catalogo *nombre_empresa)
# =====================================================================
class Catalogo(models.Model):
    codigo_catalogo = models.CharField(max_length=20, primary_key=True)
    nombre_empresa = models.CharField(max_length=150)

    class Meta:
        db_table = "catalogo"

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
        db_table = "proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return f"{self.nombre_empresa} ({self.nit})"

    @property
    def id(self):
        return self.codigo_proveedor

    @property
    def email(self):
        return self.correo

    @property
    def contacto_nombre(self):
        return self.nombre_empresa

    @property
    def categoria(self):
        return "General"


# =====================================================================
# UNIDAD_MEDIDA  (MER: #id_unidad *codigo *nombre *abreviatura -descripcion)
# Nueva tabla de referencia para normalizar unidades
# =====================================================================
class UnidadMedida(models.Model):
    """
    Tabla de referencia para unidades de medida estandarizadas.
    Garantiza consistencia en toda la aplicación.
    """

    id_unidad = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=10, unique=True, db_index=True)
    nombre = models.CharField(max_length=50, unique=True)
    abreviatura = models.CharField(max_length=10)
    descripcion = models.TextField(blank=True)

    # Para control de datos
    activa = models.BooleanField(default=True)
    orden = models.PositiveIntegerField(default=0, help_text="Para ordenar en select")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "unidad_medida"
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.abreviatura})"

    @property
    def id(self):
        return self.id_unidad


# =====================================================================
# MATERIAL_CONSTRUCCION  (MER: #cod_material *nombre *id_unidad ...)
# Normalizado con UnidadMedida (ForeignKey)
# =====================================================================
class MaterialConstruccion(models.Model):
    cod_material = models.AutoField(primary_key=True)
    catalogo = models.ForeignKey(
        Catalogo, on_delete=models.SET_NULL, null=True, blank=True, related_name="materiales"
    )
    nombre = models.CharField(max_length=100)
    unidad_medida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.PROTECT,
        related_name="materiales",
        help_text="Seleccione una unidad de medida estándar",
    )
    descripcion = models.TextField()
    precio_referencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(9999999999.99)],
    )
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = "material_construccion"
        verbose_name = "Material de Construcción"
        verbose_name_plural = "Materiales de Construcción"

    def __str__(self):
        return self.nombre

    @property
    def id(self):
        return self.cod_material

    @property
    def stock(self):
        try:
            return self.stock_info.cantidad_actual
        except Stock.DoesNotExist:
            return 0

    @property
    def precio(self):
        return self.precio_referencia

    @precio.setter
    def precio(self, value):
        self.precio_referencia = value

    @property
    def tipo(self):
        return self.catalogo.nombre_empresa if self.catalogo else ""


# =====================================================================
# STOCK  (MER: #id_material(PK)(FK) - cantidad_actual - stock_minimo - fecha_actualizacion)
# =====================================================================
class Stock(models.Model):
    material = models.OneToOneField(
        MaterialConstruccion, on_delete=models.CASCADE, primary_key=True, related_name="stock_info"
    )
    cantidad_actual = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100000)]
    )
    stock_minimo = models.IntegerField(default=10, validators=[MinValueValidator(0)])
    ubicacion = models.CharField(max_length=120, blank=True, default="")
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "stock"

    def __str__(self):
        return f"Stock {self.material.nombre}: {self.cantidad_actual}"

    @property
    def id(self):
        return self.material.cod_material

    @property
    def cantidad(self):
        return self.cantidad_actual

    @property
    def ultima_actualizacion(self):
        return self.fecha_actualizacion


# =====================================================================
# METODO_PAGO  (MER: #codigo_metodo_pago *metodo)
# =====================================================================
class MetodoPago(models.Model):
    codigo_metodo_pago = models.CharField(max_length=20, primary_key=True)
    metodo = models.CharField(max_length=50, unique=True)

    class Meta:
        db_table = "metodo_pago"
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"

    def __str__(self):
        return self.metodo


# =====================================================================
# NOTIFICACION  (FUERA del MER — NO se toca)
# =====================================================================
class Notificacion(models.Model):
    TIPOS = [
        ("info", "Información"),
        ("success", "Éxito"),
        ("warning", "Advertencia"),
        ("danger", "Error"),
    ]
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="notificaciones")
    titulo = models.CharField(max_length=100, default="Nueva notificación")
    mensaje = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPOS, default="info")
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-fecha"]
        db_table = "notificacion"

    def __str__(self):
        return f"Notif {self.usuario}: {self.mensaje[:20]}..."


Material = MaterialConstruccion
