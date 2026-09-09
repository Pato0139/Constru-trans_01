# Generated migration for factura.cliente_id cleanup - make nullable

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('facturacion', '0002_initial'),
    ]

    operations = [
        # Set all cliente_id to NULL to remove redundancy
        migrations.RunSQL(
            sql="UPDATE factura SET cliente_id = NULL;",
            reverse_sql="-- Reverse would require data recovery"
        ),
        # Make cliente_id nullable (safer than deleting immediately)
        migrations.AlterField(
            model_name='factura',
            name='cliente',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='facturas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
