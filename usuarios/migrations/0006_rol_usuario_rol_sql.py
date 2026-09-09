# Generated migration for Rol and UsuarioRol - SQL direct approach
# NOTE: tables 'rol' and 'usuario_rol' are already created in 0003_rol_usuario_rol.
# This migration focuses on the SQL seed/cleanup operations for those tables.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0005_migrate_roles_to_usuario_rol'),
    ]

    operations = [
        # Insert default roles (idempotent thanks to ON CONFLICT)
        migrations.RunSQL(
            sql=(
                "INSERT INTO rol (nombre_rol, activo) VALUES "
                "('admin', 1), ('operador', 1), ('conductor', 1), ('cliente', 1), ('proveedor', 1) "
                "ON CONFLICT (nombre_rol) DO NOTHING;"
            ),
            reverse_sql=(
                "DELETE FROM rol "
                "WHERE nombre_rol IN "
                "('admin', 'operador', 'conductor', 'cliente', 'proveedor');"
            ),
        ),
    ]
