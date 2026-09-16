# Generated migration for pago_pedido.metodo_pago normalization

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0001_initial'),
        ('usuarios', '0007_rol_usuariorol_vehiculo_catalogo_and_more'),
    ]

    # The FK and legacy text field are already defined by 0001_initial.
    operations = []
