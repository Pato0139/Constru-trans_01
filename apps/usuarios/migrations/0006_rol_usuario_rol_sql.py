# Generated migration for Rol and UsuarioRol - SQL direct approach

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_add_integrity_constraints'),
    ]

    operations = [
        # Create Rol table
        migrations.CreateModel(
            name='Rol',
            fields=[
                ('id_rol', models.AutoField(primary_key=True, serialize=False)),
                ('nombre_rol', models.CharField(max_length=50, unique=True)),
            ],
            options={
                'db_table': 'rol',
            },
        ),
        # Create UsuarioRol table
        migrations.CreateModel(
            name='UsuarioRol',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='usuarios.rol')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='usuarios.usuario')),
            ],
            options={
                'db_table': 'usuario_rol',
            },
        ),
        # Add unique constraint to UsuarioRol
        migrations.AddConstraint(
            model_name='usuariorol',
            constraint=models.UniqueConstraint(fields=['usuario', 'rol'], name='uq_usuario_rol'),
        ),
        # Insert default roles
        migrations.RunPython(
            code=migrations.RunSQL(
                "INSERT INTO rol (nombre_rol) VALUES "
                "('admin'), ('operador'), ('conductor'), ('cliente'), ('proveedor') "
                "ON CONFLICT (nombre_rol) DO NOTHING;"
            ).code,
            reverse_code=migrations.RunSQL("DELETE FROM rol WHERE nombre_rol IN ('admin', 'operador', 'conductor', 'cliente', 'proveedor');").code,
        ),
    ]
