# Generated migration for Rol and UsuarioRol normalization (3FN)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_alter_vehiculo_estado'),
    ]

    operations = [
        # Create Rol table
        migrations.CreateModel(
            name='Rol',
            fields=[
                ('id_rol', models.AutoField(primary_key=True, serialize=False)),
                ('nombre_rol', models.CharField(max_length=50, unique=True)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Rol',
                'verbose_name_plural': 'Roles',
                'db_table': 'rol',
            },
        ),
        # Create UsuarioRol table (Many-to-Many relationship)
        migrations.CreateModel(
            name='UsuarioRol',
            fields=[
                ('id_usuario_rol', models.AutoField(primary_key=True, serialize=False)),
                ('fecha_asignacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_revocacion', models.DateTimeField(blank=True, null=True)),
                ('activo', models.BooleanField(default=True)),
                ('rol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usuarios', to='usuarios.rol')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usuario_roles', to='usuarios.usuario')),
            ],
            options={
                'verbose_name': 'Usuario Rol',
                'verbose_name_plural': 'Usuario Roles',
                'db_table': 'usuario_rol',
                'unique_together': {('usuario', 'rol')},
            },
        ),
    ]
