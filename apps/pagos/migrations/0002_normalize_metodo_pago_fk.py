# Generated migration for pago_pedido.metodo_pago normalization

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0001_initial'),
        ('usuarios', '0006_rol_usuario_rol_sql'),
    ]

    operations = [
        # Add new FK column
        migrations.AddField(
            model_name='pago_pedido',
            name='codigo_metodo_pago_fk',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=models.deletion.PROTECT,
                to='usuarios.metodo_pago',
                db_column='codigo_metodo_pago_fk'
            ),
        ),
        # Migrate existing data
        migrations.RunSQL(
            sql="UPDATE pago_pedido SET codigo_metodo_pago_fk = metodo_pago WHERE metodo_pago IS NOT NULL;",
            reverse_sql="UPDATE pago_pedido SET codigo_metodo_pago_fk = NULL;"
        ),
        # Make FK required
        migrations.AlterField(
            model_name='pago_pedido',
            name='codigo_metodo_pago_fk',
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                to='usuarios.metodo_pago',
                db_column='codigo_metodo_pago_fk'
            ),
        ),
        # Remove old text column
        migrations.RemoveField(
            model_name='pago_pedido',
            name='metodo_pago',
        ),
        # Rename FK to original name
        migrations.RenameField(
            model_name='pago_pedido',
            old_name='codigo_metodo_pago_fk',
            new_name='codigo_metodo_pago',
        ),
    ]
