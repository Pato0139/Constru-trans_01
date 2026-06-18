
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.usuarios.models import Usuario, Conductor, EPS
from datetime import date, timedelta
from django.db import connections

def add_conductor_to_db(db_alias):
    print(f"Adding conductor to {db_alias}...")
    
    # Ensure EPS exists
    eps, _ = EPS.objects.using(db_alias).get_or_create(
        codigo_eps='EPS001',
        defaults={
            'numero_seguro': '123456789',
            'ciudad': 'Bogota',
            'direccion': 'Calle 100 # 10-10',
            'telefono': '3101234567',
            'correo': 'contacto@eps.com',
        },
    )

    # Create user
    usuario, created = Usuario.objects.using(db_alias).get_or_create(
        username='conductor_test',
        defaults={
            'email': 'conductor@test.com',
            'nombres': 'Juan',
            'apellidos': 'Perez',
            'documento': '12345678',
            'tipo_documento': 'CC',
            'rol': 'conductor',
            'estado': 'activo',
        }
    )

    if created:
        usuario.set_password('Conductor123!')
        usuario.save(using=db_alias)
        print(f"Created user conductor_test in {db_alias}")
    else:
        print(f"User conductor_test already exists in {db_alias}")

    # Create conductor profile
    Conductor.objects.using(db_alias).get_or_create(
        usuario=usuario,
        defaults={
            'numero_licencia': 'LIC-123456',
            'categoria_licencia': 'C2',
            'fecha_vencimiento_licencia': date.today() + timedelta(days=365),
            'estado': 'activo',
            'eps': eps,
        }
    )

# Add to both databases
add_conductor_to_db('default')
add_conductor_to_db('remota')

print("Done! Conductor added to both databases!")
