import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Orden',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('fecha_entrega_programada', models.DateTimeField(blank=True, null=True)),
                ('fecha_toma_entrega', models.DateTimeField(blank=True, null=True)),
                ('fecha_entrega_real', models.DateTimeField(blank=True, null=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('en_ruta', 'En Ruta'), ('entregado', 'Entregado'), ('cancelado', 'Cancelado')], default='pendiente', max_length=20)),
                ('precio', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ordenes_cliente', to='usuarios.usuario')),
                ('conductor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordenes_conductor', to='usuarios.usuario')),
            ],
            options={
                'ordering': ['-fecha'],
            },
        ),
        migrations.CreateModel(
            name='DetalleOrden',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad', models.IntegerField(default=1)),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=10)),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='usuarios.material')),
                ('orden', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='detalles', to='ordenes.orden')),
            ],
        ),
        migrations.CreateModel(
            name='Entrega',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('en_ruta', 'En Ruta'), ('entregado', 'Entregado')], default='pendiente', max_length=20)),
                ('conductor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='usuarios.usuario')),
                ('vehiculo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='usuarios.vehiculo')),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entregas', to='ordenes.orden')),
            ],
            options={
                'ordering': ['-fecha'],
            },
        ),
    ]
