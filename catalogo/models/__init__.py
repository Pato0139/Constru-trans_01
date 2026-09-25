from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings

from usuarios.models import Usuario


numeric_and_space_validator = []


class Catalogo(models.Model):
    codigo_catalogo = models.CharField(max_length=20, primary_key=True)
    nombre_empresa = models.CharField(max_length=150)

    class Meta:
        db_table = "catalogo"

    def __str__(self):
        return self.nombre_empresa


class UnidadMedida(models.Model):
    id_unidad = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=10, unique=True, db_index=True)
    nombre = models.CharField(max_length=50, unique=True)
    abreviatura = models.CharField(max_length=10)
    descripcion = models.TextField(blank=True)

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


class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "marca"
        ordering = ["nombre"]
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"

    def __str__(self):
        return self.nombre


class MaterialConstruccion(models.Model):
    cod_material = models.AutoField(primary_key=True)
    catalogo = models.ForeignKey(
        Catalogo, on_delete=models.SET_NULL, null=True, blank=True, related_name="materiales"
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materiales",
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
        validators=[MinValueValidator(0.01), MaxValueValidator(9999999999.99)],
    )
    activo = models.BooleanField(default=True, help_text="Indica si el material está disponible para uso")
    sincronizado = models.BooleanField(default=False)

    class Meta:
        db_table = "material_construccion"
        verbose_name = "Material de Construcción"
        verbose_name_plural = "Materiales de Construcción"
        permissions = (
            ("gestionar_inventario", "Puede gestionar inventario"),
        )
        constraints = [
            models.CheckConstraint(
                check=models.Q(precio_referencia__gte=0),
                name="chk_material_precio_referencia_gte_0",
            ),
        ]

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


Material = MaterialConstruccion


class HistorialPrecioMaterial(models.Model):
    material = models.ForeignKey(MaterialConstruccion, on_delete=models.CASCADE, related_name="historial_precios")
    precio_anterior = models.DecimalField(max_digits=12, decimal_places=2)
    precio_nuevo = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="cambios_precios")
    observaciones = models.TextField(blank=True, help_text="Detalles o razones del cambio de precio")
    mes = models.IntegerField(editable=False)
    año = models.IntegerField(editable=False)

    class Meta:
        db_table = "historial_precio_material"
        ordering = ["-fecha_cambio"]
        verbose_name = "Historial de Precio"
        verbose_name_plural = "Historial de Precios"

    def __str__(self):
        return f"{self.material.nombre} - {self.fecha_cambio.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        if not self.mes:
            self.mes = self.fecha_cambio.month
        if not self.año:
            self.año = self.fecha_cambio.year
        super().save(*args, **kwargs)


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
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad_actual__gte=0),
                name="chk_stock_cantidad_actual_gte_0",
            ),
            models.CheckConstraint(
                check=models.Q(stock_minimo__gte=0),
                name="chk_stock_minimo_gte_0",
            ),
        ]

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


from .conteos import SesionConteo, ConteoItem
from .lotes import LoteMaterial
from .movimientos import MovimientoInventario
