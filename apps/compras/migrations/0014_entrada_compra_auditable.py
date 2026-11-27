import uuid

import django.utils.timezone
import config.validators
from django.db import migrations, models


def backfill_entry_snapshots(apps, schema_editor):
    Detalle = apps.get_model("compras", "DetalleCompra")
    alias = schema_editor.connection.alias
    for detalle in Detalle.objects.using(alias).select_related("material", "material__unidad_medida").iterator():
        material = detalle.material
        detalle.material_nombre = material.nombre or ""
        unidad = material.unidad_medida
        detalle.unidad_medida_nombre = unidad.nombre if unidad else ""
        detalle.unidad_medida_abreviatura = unidad.abreviatura if unidad else ""
        # El precio de venta histórico no existe en las compras antiguas: no se inventa.
        detalle.save(update_fields=["material_nombre", "unidad_medida_nombre", "unidad_medida_abreviatura"], using=alias)


def populate_idempotency_keys(apps, schema_editor):
    Compra = apps.get_model("compras", "Compra")
    alias = schema_editor.connection.alias
    for compra in Compra.objects.using(alias).filter(clave_idempotencia__isnull=True).iterator():
        compra.clave_idempotencia = uuid.uuid4()
        compra.save(update_fields=["clave_idempotencia"], using=alias)


class Migration(migrations.Migration):
    dependencies = [
        ("compras", "0013_alter_proveedor_telefono"),
        ("catalogo", "0011_stock_minimo_default_zero"),
    ]

    operations = [
        migrations.AddField(
            model_name="compra",
            name="numero_factura",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="compra",
            name="motivo_anulacion",
            field=models.TextField(blank=True, default="", validators=[config.validators.texto_multilinea]),
        ),
        migrations.AddField(
            model_name="compra",
            name="clave_idempotencia",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.RunPython(populate_idempotency_keys, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="compra",
            name="clave_idempotencia",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name="compra",
            name="fecha_compra",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name="detallecompra",
            name="material_nombre",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="detallecompra",
            name="unidad_medida_nombre",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="detallecompra",
            name="unidad_medida_abreviatura",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
        migrations.AddField(
            model_name="detallecompra",
            name="precio_venta_unitario",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.RunPython(backfill_entry_snapshots, migrations.RunPython.noop),
    ]
