# Generated migration for comprehensive CHECK constraints
# PATCHED: Stock/Material constraints already created in 0004_add_integrity_constraints.
# Wrapped in SeparateDatabaseAndState with empty database_operations to prevent
# "constraint already exists" errors.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0006_rol_usuario_rol_sql'),
        ('ordenes', '0003_conductor_fk_to_conductor'),
        ('compras', '0002_add_integrity_constraints'),
    ]

    operations = [
        # --- CONFLICT: chk_stock_cantidad_actual_gte_0 already in 0004 ---
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name='stock',
                    constraint=models.CheckConstraint(
                        check=models.Q(cantidad_actual__gte=0),
                        name='chk_stock_cantidad_actual_gte_0'
                    ),
                ),
            ],
            database_operations=[],
        ),
        # --- CONFLICT: chk_stock_minimo_gte_0 already in 0004 ---
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name='stock',
                    constraint=models.CheckConstraint(
                        check=models.Q(stock_minimo__gte=0),
                        name='chk_stock_minimo_gte_0'
                    ),
                ),
            ],
            database_operations=[],
        ),
        # --- CONFLICT: chk_material_precio_referencia_gte_0 already in 0004 ---
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    model_name='materialconstruccion',
                    constraint=models.CheckConstraint(
                        check=models.Q(precio_referencia__gte=0),
                        name='chk_material_precio_referencia_gte_0'
                    ),
                ),
            ],
            database_operations=[],
        ),
        # NOTE: chk_pago_monto_gt_0 already defined in pagos/0001_initial (app pagos).
        # Cannot be created from app 'usuarios' via AddConstraint, so it is omitted here.
    ]
