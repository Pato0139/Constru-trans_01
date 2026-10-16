from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.catalogo.models import MaterialConstruccion
from config.state_machine import TransicionMixin
from config.validators import (
    cantidad_validators,
    monto_positivo,
    nit_validator,
    no_negativo,
    no_solo_espacios,
    porcentaje_validators,
    telefono_validator,
)


# =====================================================================
# PROVEEDOR
# =====================================================================
class Proveedor(models.Model):
    codigo_proveedor = models.AutoField(primary_key=True)
    nombre_empresa = models.CharField(max_length=150, validators=[no_solo_espacios])
    nit = models.CharField(max_length=20, unique=True, validators=[nit_validator])
    contacto_nombre = models.CharField(max_length=150, blank=True, validators=[no_solo_espacios])
    telefono = models.CharField(max_length=20, validators=[telefono_validator])
    correo = models.EmailField(blank=True)
    direccion = models.CharField(max_length=255, blank=True, validators=[no_solo_espacios])
    ciudad = models.CharField(max_length=100, blank=True, validators=[no_solo_espacios])
    categoria = models.CharField(max_length=100, blank=True, default="General", validators=[no_solo_espacios])
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
class Compra(TransicionMixin, models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("recibida", "Recibida"), ("cancelada", "Cancelada")]
    ESTADO_CAMPO = "estado"
    TRANSICIONES = {
        "pendiente": ["recibida", "cancelada"],
        "recibida": [],
        "cancelada": [],
    }

    id_compra = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, db_column="codigo_proveedor")
    fecha_compra = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=porcentaje_validators)
    total_compra = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])
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
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0),
                name="chk_compra_subtotal_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(impuesto__gte=0),
                name="chk_compra_impuesto_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(impuesto_porcentaje__gte=0) & models.Q(impuesto_porcentaje__lte=100),
                name="chk_compra_impuesto_pct_rango",
            ),
        ]

    def __str__(self):
        return f"{self.numero_orden} - {self.proveedor.nombre_empresa}"

    @property
    def numero_orden(self):
        return f"OC-{self.fecha_compra.year}-{self.id_compra:04d}"

    def clean(self):
        super().clean()
        if self.subtotal is not None and self.subtotal < 0:
            raise ValidationError({"subtotal": "El subtotal no puede ser negativo."})
        if self.impuesto is not None and self.impuesto < 0:
            raise ValidationError({"impuesto": "El impuesto no puede ser negativo."})
        if self.impuesto_porcentaje is not None and not (0 <= self.impuesto_porcentaje <= 100):
            raise ValidationError({"impuesto_porcentaje": "El porcentaje de impuesto debe estar entre 0 y 100."})
        if self.total_compra is not None and self.total_compra < 0:
            raise ValidationError({"total_compra": "El total no puede ser negativo."})

    def calcular_total(self, using=None):
        if using is None:
            using = self._state.db
        self.subtotal = sum(
            (detalle.subtotal for detalle in self.detalles.using(using).all()),
            Decimal("0.00"),
        )
        self.impuesto = Decimal("0.00")
        self.total_compra = self.subtotal + self.impuesto
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
        max_digits=12, decimal_places=2, validators=[monto_positivo]
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
            ),
            models.CheckConstraint(
                check=models.Q(precio_actual__gt=0),
                name="chk_provmat_precio_actual_gt_0",
            ),
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
    cantidad = models.PositiveIntegerField(validators=cantidad_validators)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[monto_positivo])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[no_negativo])

    class Meta:
        db_table = "detalle_compra"
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name="chk_detalle_compra_cantidad_gt_0",
            ),
            models.CheckConstraint(
                check=models.Q(precio_unitario__gt=0),
                name="chk_detalle_compra_precio_unitario_gt_0",
            ),
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0),
                name="chk_detalle_compra_subtotal_gte_0",
            ),
            models.UniqueConstraint(
                fields=["compra", "material"],
                name="uq_detalle_compra_compra_material",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.material.nombre}"

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad debe ser mayor a 0."})
        if self.precio_unitario is not None and self.precio_unitario <= Decimal("0"):
            raise ValidationError({"precio_unitario": "El precio unitario debe ser mayor a 0."})

    def save(self, *args, **kwargs):
        using = kwargs.get("using", self._state.db)
        self.full_clean()
        self.subtotal = Decimal(self.cantidad) * Decimal(str(self.precio_unitario))
        super().save(*args, **kwargs)
        self.compra.calcular_total(using=using)
