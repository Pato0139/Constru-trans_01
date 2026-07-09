# Merge migration generado para resolver conflicto entre:
# 0003_alter_pago_monto y 0003_alter_pago_monto_pagopedido

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pagos', '0003_alter_pago_monto'),
        ('pagos', '0003_alter_pago_monto_pagopedido'),
    ]

    operations = [
    ]
