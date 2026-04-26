
import os
import sys
import django
import random
from pathlib import Path

# Añadir el directorio raíz al sys.path para que Django pueda encontrar los módulos
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Configuración de Django - DEBE IR ANTES DE CUALQUIER IMPORT DE MODELOS
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Usuario, Material
from apps.clientes.models import Cliente

def cleanup_and_create_data():
    print("Iniciando limpieza de perfiles incorrectos...")
    # 1. Eliminar perfiles de cliente para usuarios que no son clientes
    incorrectos = Cliente.objects.exclude(usuario__rol='cliente')
    count = incorrectos.count()
    for c in incorrectos:
        print(f"Eliminando perfil de cliente para {c.usuario.nombres} (Rol: {c.usuario.rol})")
        c.delete()
    print(f"Se eliminaron {count} perfiles incorrectos.")

    # 2. Crear/Actualizar Usuarios de Prueba
    names = [
        ('Carlos', 'Perez', 'cliente', 'Constructora Perez SAS', '800.123.456-1'),
        ('Maria', 'Gomez', 'admin', None, None),
        ('Luis', 'Rodriguez', 'conductor', None, None),
        ('Ana', 'Martinez', 'cliente', 'Ferretería Ana', '900.987.654-2')
    ]
    
    for n, a, r, empresa, nit in names:
        email = f'{n.lower()}@test.com'
        user, created = User.objects.get_or_create(username=email, email=email)
        if created:
            user.set_password('123456789')
            user.save()
        
        perfil, _ = Usuario.objects.get_or_create(
            user=user,
            defaults={
                'nombres': n,
                'apellidos': a,
                'rol': r,
                'tipo_documento': 'CC',
                'documento': str(random.randint(1000000, 9999999)),
                'sincronizado': False
            }
        )
        
        # Si es cliente, poblar su perfil de negocio
        if r == 'cliente':
            cliente_obj, _ = Cliente.objects.get_or_create(usuario=perfil)
            cliente_obj.razon_social = empresa
            cliente_obj.nit_rut = nit
            cliente_obj.direccion_fiscal = f"Calle {random.randint(1, 100)} # {random.randint(1, 100)}"
            cliente_obj.ciudad = random.choice(['Bogotá', 'Medellín', 'Cali', 'Barranquilla'])
            cliente_obj.save()
            print(f"Perfil de Cliente para {n} actualizado.")
            
        # Forzar re-sincronización
        perfil.sincronizado = False
        perfil.save()

    # 3. Actualizar Alvaro si existe
    try:
        alvaro = Usuario.objects.get(nombres='Alvaro')
        cliente_alvaro, _ = Cliente.objects.get_or_create(usuario=alvaro)
        cliente_alvaro.razon_social = "Inversiones Alvaro"
        cliente_alvaro.nit_rut = "700.555.444-9"
        cliente_alvaro.direccion_fiscal = "Av. Siempre Viva 123"
        cliente_alvaro.ciudad = "Bogotá"
        cliente_alvaro.save()
        alvaro.sincronizado = False
        alvaro.save()
        print("Perfil de Alvaro actualizado y listo para sincronizar.")
    except Usuario.DoesNotExist:
        pass

    # 4. Forzar re-sincronización de materiales también
    Material.objects.all().update(sincronizado=False)
    print("Materiales marcados para re-sincronizar.")

if __name__ == '__main__':
    print("Creando/Actualizando datos de prueba y limpiando base de datos...")
    cleanup_and_create_data()
    print("¡Proceso completado! Ejecuta 'python manage.py sincronizar --once'")
