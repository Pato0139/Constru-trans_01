import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test import Client
from django.urls import reverse
from apps.usuarios.models import Usuario, Conductor, Vehiculo, ConductorVehiculo

Usuario.objects.filter(username__in=['admin@test.com','cond@test.com']).delete()
Vehiculo.objects.filter(placa__in=['ABC123','DEF456']).delete()

admin_user = Usuario.objects.create_user(
    username='admin@test.com',
    email='admin@test.com',
    password='password123',
    rol='admin',
    nombres='Admin',
    documento='1001',
    tipo_documento='CC'
)
conductor_user = Usuario.objects.create_user(
    username='cond@test.com',
    email='cond@test.com',
    password='password123',
    rol='conductor',
    nombres='Conductor',
    documento='1003',
    tipo_documento='CC'
)
conductor_profile = Conductor.objects.create(
    usuario=conductor_user,
    numero_licencia='LIC-1003',
    categoria_licencia='C2',
    fecha_vencimiento_licencia=date.today()+timedelta(days=365),
    estado='activo'
)
vehiculo = Vehiculo.objects.create(
    placa='ABC123',
    marca='Toyota',
    modelo='Hiace',
    tipo_vehiculo='Bolqueta',
    capacidad_carga=10.00,
    estado='disponible'
)

client = Client()
client.login(username='admin@test.com', password='password123')
response = client.post(reverse('usuarios:asignar_vehiculo_conductor', args=[conductor_user.id]), {'vehiculo': str(vehiculo.id_vehiculo)})
print('status', response.status_code)
print('redirect', getattr(response, 'url', None))
print('context_empty', response.context is None)
print('form_errors', response.context['form'].errors if response.context and 'form' in response.context else 'no form')
print('content_snippet', response.content[:1000])
print('count', ConductorVehiculo.objects.filter(conductor=conductor_profile).count())
