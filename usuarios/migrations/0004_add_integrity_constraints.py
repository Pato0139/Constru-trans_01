# Generated migration for Stock, MaterialConstruccion, and Vehiculo constraints
# Adds CHECK constraints for data integrity

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0003_rol_usuario_rol'),
    ]

    operations = [
        # Add constraints to Stock
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
        # Add constraint to MaterialConstruccion
        migrations.AddConstraint(
            model_name='materialconstruccion',
            constraint=models.CheckConstraint(
                check=models.Q(precio_referencia__gte=0),
                name='chk_material_precio_referencia_gte_0'
            ),
        ),
        # Add constraint to Vehiculo
        migrations.AddConstraint(
            model_name='vehiculo',
            constraint=models.CheckConstraint(
                check=models.Q(capacidad_carga__gt=0),
                name='chk_vehiculo_capacidad_carga_gt_0'
            ),
        ),
    ]
