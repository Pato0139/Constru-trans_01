# Generated migration for Factura normalization (3FN)
# Removes redundant cliente FK and adds constraints

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('facturacion', '0001_initial'),
        ('ordenes', '0002_normalize_conductor_fk'),
    ]

    operations = [
        # Remove cliente FK from Factura (data will be obtained through pedido)
        migrations.RemoveField(
            model_name='factura',
            name='cliente',
        ),
        # Make pedido non-nullable (each factura must have a pedido)
        migrations.AlterField(
            model_name='factura',
            name='pedido',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT, 
                related_name='factura', 
                to='ordenes.pedido'
            ),
        ),
        # Add CHECK constraints to Factura
        migrations.AddConstraint(
            model_name='factura',
            constraint=models.CheckConstraint(
                check=models.Q(subtotal__gte=0),
                name='chk_factura_subtotal_gte_0'
            ),
        ),
        migrations.AddConstraint(
            model_name='factura',
            constraint=models.CheckConstraint(
                check=models.Q(iva__gte=0),
                name='chk_factura_iva_gte_0'
            ),
        ),
        migrations.AddConstraint(
            model_name='factura',
            constraint=models.CheckConstraint(
                check=models.Q(total__gte=0),
                name='chk_factura_total_gte_0'
            ),
        ),
    ]
