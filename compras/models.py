from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator


numeric_and_space_validator = RegexValidator(
    r"^[0-9 ]+$",
    message="Este campo solo puede contener números y espacios.",
)


from catalogo.models import MaterialConstruccion


# =====================================================================
# PROVEEDOR
# =====================================================================
class Proveedor(models.Model):
    codigo_proveedor = models.AutoField(primary_key=True)
    nombre_empresa = models.CharField(max_length=150)
    nit = models.CharField(max_length=20, unique=True, validators=[numeric_and_space_validator])
    contacto_nombre = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=20, validators=[numeric_and_space_validator])
    correo = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    categoria = models.CharField(max_length=100, blank=True, default="General")
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
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

    @email.setter
    def email(self, value):
        self.correo = value

    @property
    def nombre(self):
        return self.nombre_empresa

    @property
    def contacto(self):
        return self.contacto_nombre

    def save(self, *args, **kwargs):
        if not self.contacto_nombre:
            self.contacto_nombre = self.nombre_empresa
        if not self.categoria:
            self.categoria = "General"
        super().save(*args, **kwargs)


# =====================================================================
# COMPRA
# =====================================================================
class Compra(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("recibida", "Recibida"), ("cancelada", "Cancelada")]

    id_compra = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, db_column="codigo_proveedor")
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="compras"
    )

    # Fuera del MER pero útil — NO se toca
    observaciones = models.TextField(blank=True, null=True)
    sincronizado = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha_compra"]
        db_table = "compra"
        permissions = (
            ("aprobar_compra", "Puede aprobar compras"),
            ("gestionar_proveedor", "Puede gestionar proveedores"),
        )
        constraints = [
            models.CheckConstraint(
                check=models.Q(total_compra__gte=0),
                name="chk_compra_total_compra_gte_0",
            ),
        ]

    def __str__(self):
        return f"{self.numero_orden} - {self.proveedor.nombre_empresa}"

    @property
    def numero_orden(self):
        return f"OC-{self.fecha_compra.year}-{self.id_compra:04d}"

    def calcular_total(self, using=None):
        if using is None:
            using = self._state.db
        self.total_compra = sum(d.subtotal for d in self.detalles.using(using).all())
        self.save(using=using)
        return self.total_compra


# =====================================================================
# PROVEEDOR_MATERIAL
# =====================================================================
class ProveedorMaterial(models.Model):
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.CASCADE, related_name="materiales_ofertados"
    )
    material = models.ForeignKey(
        MaterialConstruccion, on_delete=models.PROTECT, related_name="proveedores_ofertantes"
    )
    precio_actual = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    referencia_proveedor = models.CharField(max_length=100, blank=True)
    observaciones = models.CharField(max_length=255, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "proveedor_material"
        ordering = ["proveedor__nombre_empresa", "material__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["proveedor", "material"], name="unique_material_por_proveedor"
            )
        ]

    def __str__(self):
        return f"{self.proveedor.nombre_empresa} - {self.material.nombre}"

    @property
    def precio_proveedor(self):
        return self.precio_actual

    @precio_proveedor.setter
    def precio_proveedor(self, value):
        self.precio_actual = value


# =====================================================================
# DETALLE_COMPRA 
# =====================================================================
class DetalleCompra(models.Model):
    id_detalle_compra = models.AutoField(primary_key=True)
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name="detalles", db_column="id_compra")
    material = models.ForeignKey(MaterialConstruccion, on_delete=models.PROTECT, db_column="cod_material")
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])

    class Meta:
        db_table = "detalle_compra"
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name="chk_detalle_compra_cantidad_gt_0",
            ),
            models.CheckConstraint(
                check=models.Q(precio_unitario__gte=0),
                name="chk_detalle_compra_precio_unitario_gte_0",
            ),
            models.UniqueConstraint(
                fields=["compra", "material"],
                name="uq_detalle_compra_compra_material",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.material.nombre}"

    def save(self, *args, **kwargs):
        using = kwargs.get("using", self._state.db)
        super().save(*args, **kwargs)
        self.compra.calcular_total(using=using)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario