# Generated migration to migrate existing roles to UsuarioRol table

from django.db import migrations


def migrate_roles_forward(apps, schema_editor):
    """
    Migrate existing usuario.rol values to usuario_rol table.
    Creates default Rol records if they don't exist.
    """
    Usuario = apps.get_model('usuarios', 'Usuario')
    Rol = apps.get_model('usuarios', 'Rol')
    UsuarioRol = apps.get_model('usuarios', 'UsuarioRol')
    
    # Create default roles if they don't exist
    roles_dict = {}
    for nombre in ['admin', 'cliente', 'conductor', 'empleado']:
        rol, _ = Rol.objects.get_or_create(
            nombre_rol=nombre,
            defaults={'descripcion': f'Rol de {nombre}', 'activo': True}
        )
        roles_dict[nombre] = rol
    
    # Migrate existing usuario.rol to usuario_rol
    for usuario in Usuario.objects.all():
        if usuario.rol and usuario.rol in roles_dict:
            rol = roles_dict[usuario.rol]
            # Only create if it doesn't exist
            UsuarioRol.objects.get_or_create(
                usuario=usuario,
                rol=rol,
                defaults={'activo': True}
            )


def migrate_roles_backward(apps, schema_editor):
    """
    Backward migration: delete usuario_rol records (keep campo rol for compatibility).
    """
    UsuarioRol = apps.get_model('usuarios', 'UsuarioRol')
    UsuarioRol.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0004_add_integrity_constraints'),
    ]

    operations = [
        migrations.RunPython(migrate_roles_forward, migrate_roles_backward),
    ]
