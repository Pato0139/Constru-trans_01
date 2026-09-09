# Generated migration for Compra/DetalleCompra normalization
# Adds CHECK and UNIQUE constraints for data integrity

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0001_initial'),
        ('facturacion', '0002_normalize_factura_3fn'),
    ]

    operations = [
        # Add constraints to Compra
        migrations.AddConstraint(
            model_name='compra',
            constraint=models.CheckConstraint(
                check=models.Q(total_compra__gte=0),
                name='chk_compra_total_compra_gte_0'
            ),
        ),
        # Add constraints to DetalleCompra
        migrations.AddConstraint(
            model_name='detallecompra',
            constraint=models.CheckConstraint(
                check=models.Q(cantidad__gt=0),
                name='chk_detalle_compra_cantidad_gt_0'
            ),
        ),
        migrations.AddConstraint(
            model_name='detallecompra',
            constraint=models.CheckConstraint(
                check=models.Q(precio_unitario__gte=0),
                name='chk_detalle_compra_precio_unitario_gte_0'
            ),
        ),
        migrations.AddConstraint(
            model_name='detallecompra',
            constraint=models.UniqueConstraint(
                fields=['compra', 'material'],
                name='uq_detalle_compra_compra_material'
            ),
        ),
    ]
