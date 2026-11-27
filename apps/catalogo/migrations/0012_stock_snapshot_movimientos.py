from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0011_stock_minimo_default_zero")]

    operations = [
        migrations.AddField(
            model_name="movimientoinventario",
            name="stock_anterior",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="stock_posterior",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
