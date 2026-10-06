import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django

django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from catalogo.models import MaterialConstruccion, UnidadMedida
from compras.models import Compra, DetalleCompra, Proveedor

User = get_user_model()
User.objects.filter(username='fixcheck').delete()

u = User.objects.create_user(
    username='fixcheck',
    email='fixcheck@test.com',
    password='123456',
    nombres='Fix',
    apellidos='Check',
    documento='12345678',
    tipo_documento='CC',
    rol='admin',
)

unidad = UnidadMedida.objects.create(codigo='UNDCHK', nombre='Unidad', abreviatura='u')
material = MaterialConstruccion.objects.create(
    nombre='Cemento Fix',
    unidad_medida=unidad,
    descripcion='x',
    precio_referencia=1000,
)
prov = Proveedor.objects.create(
    nombre_empresa='Prov Fix',
    nit='9000000001',
    telefono='3000000001',
    correo='p@test.com',
)
compra = Compra.objects.create(proveedor=prov, usuario=u)
DetalleCompra.objects.create(compra=compra, material=material, cantidad=2, precio_unitario=1500)

c = Client()
assert c.login(username='fixcheck', password='123456'), 'login failed'
resp = c.get('/compras/')
html = resp.content.decode('utf-8')
print('STATUS', resp.status_code)
print('THEME_OK', 'data-theme="light"' in html)
print('COUNT_OK', '2' in html)
print('FIRST_THEME_SNIPPET', html[html.find('data-theme'):html.find('data-theme') + 500])
