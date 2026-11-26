from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0010_alter_catalogo_nombre_empresa")]

    operations = [
        migrations.AlterField(
            model_name="stock",
            name="stock_minimo",
            field=models.IntegerField(default=0, validators=[MinValueValidator(0)]),
        ),
    ]
