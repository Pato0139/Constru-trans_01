import os
import sys
import django

# Añadir la raíz del proyecto al sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configurar el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Usuario

def create_global_admin():
    username = 'Edward_Fonseca'
    email = 'edwardf5432@gmail.com'
    password = 'Davit12345'

    print(f"Verificando usuario global: {username}...")

    # 1. Crear o actualizar el User de Django
    user, created = User.objects.get_or_create(username=username)
    
    user.email = email
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    user.save()

    if created:
        print(f"[OK] Usuario {username} creado exitosamente.")
    else:
        print(f"[OK] Usuario {username} actualizado con nuevas credenciales.")

    # 2. Crear o actualizar el perfil de Usuario
    perfil, p_created = Usuario.objects.get_or_create(user=user)
    
    perfil.nombres = "Edward"
    perfil.apellidos = "Fonseca"
    perfil.rol = 'admin'
    perfil.estado = 'activo'
    perfil.save()

    if p_created:
        print(f"[OK] Perfil de Usuario para {username} creado como Administrador.")
    else:
        print(f"[OK] Perfil de Usuario para {username} verificado.")

if __name__ == "__main__":
    create_global_admin()
