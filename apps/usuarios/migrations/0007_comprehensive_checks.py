# Generated migration for comprehensive CHECK constraints

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_rol_usuario_rol_sql'),
        ('ordenes', '0003_conductor_fk_to_conductor'),
        ('compras', '0002_add_integrity_constraints'),
    ]

    operations = [
        # Stock checks
        migrations.AddConstraint(
            model_name='stock',
            constraint=models.CheckConstraint(
                check=models.Q(cantidad_actual__gte=0),
                name='chk_stock_cantidad_actual_gte_0'
            ),
        ),
        migrations.AddConstraint(
            model_name='stock',
            constraint=models.CheckConstraint(
                check=models.Q(stock_minimo__gte=0),
                name='chk_stock_minimo_gte_0'
            ),
        ),
        
        # Material checks
        migrations.AddConstraint(
            model_name='materialconstruccion',
            constraint=models.CheckConstraint(
                check=models.Q(precio_referencia__gte=0),
                name='chk_material_precio_referencia_gte_0'
            ),
        ),
        
        # Pago checks
        migrations.AddConstraint(
            model_name='pago',
            constraint=models.CheckConstraint(
                check=models.Q(monto__gt=0),
                name='chk_pago_monto_gt_0'
            ),
        ),
    ]
