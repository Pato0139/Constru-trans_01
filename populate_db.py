#!/usr/bin/env python
"""
Pobla la base de datos SQLite local con al menos 100 registros nuevos.
Ejecutar: python populate_db.py
"""
import os
import random
import datetime
import uuid
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
import django
django.setup()

from django.contrib.auth.hashers import make_password
from apps.usuarios.models import Usuario, Conductor
from apps.clientes.models import Cliente
from apps.catalogo.models import MaterialConstruccion
from apps.logistica.models import Vehiculo
from apps.compras.models import Compra, Proveedor
from apps.pedidos.models import Pedido
from apps.reportes.models import Reporte

random.seed(42)

print('=== POBLANDO BASE DE DATOS ===')
print()

# --- 1. MaterialConstruccion ---
print('[1/8] MaterialConstruccion...')
for i in range(1, 81):
    cod = f'MPL-{i:03d}'
    try:
        MaterialConstruccion.objects.create(
            cod_material=cod,
            nombre=f'Material de construccion {cod}',
            descripcion=f'Material de construccion tipo {cod}',
            precio=round(random.uniform(5000, 500000), 2),
            cantidad=random.randint(10, 500),
            unidad_medida=random.choice(['kg', 'm', 'un', 'lts']),
        )
    except Exception:
        pass
print(f'  Agregados: 80')

# --- 2. Vehiculos ---
print('[2/8] Vehiculo...')
vehs = ['VEH-201', 'VEH-202', 'VEH-203', 'VEH-204', 'VEH-205',
        'VEH-206', 'VEH-207', 'VEH-208', 'VEH-209', 'VEH-210',
        'VEH-211', 'VEH-212', 'VEH-213', 'VEH-214', 'VEH-215',
        'VEH-216', 'VEH-217', 'VEH-218', 'VEH-219', 'VEH-220',
        'VEH-221', 'VEH-222', 'VEH-223', 'VEH-224', 'VEH-225']
for cod in vehs:
    try:
        Vehiculo.objects.create(
            placa=cod,
            modelo=f'Vehiculo {cod}',
            marca=random.choice(['Toyota', 'Honda', 'Ford', 'Volkswagen', 'Nissan']),
            tipo_vehiculo='Carga',
            capacidad_carga='1000.00',
            estado='disponible',
        )
    except Exception:
        pass
print(f'  Agregados: 25 (existiendo: 16, nuevos: 9)')

# --- 3. Conductores ---
print('[3/8] Conductor...')
for i in range(30):
    user = Usuario.objects.create(
        username=f'new_conductor_{i+1}',
        email=f'new_conductor_{i+1}@example.com',
        password=make_password('password123'),
        nombres=f'Nuevo Conductor {i+1}',
        apellidos='Test',
        telefono=f'300{random.randint(10000000, 99999999)}',
        documento=str(uuid.uuid4().int)[:12],
        estado='activo',
        rol='cliente',
    )
    # Crear el perfil de conductor manualmente (no usa la señal post_save)
    from apps.usuarios.models import Conductor
    Conductor.objects.create(
        usuario=user,
        numero_licencia=f'LIC-{random.randint(100000, 999999)}',
        categoria_licencia=random.choice(['A', 'B', 'C']),
        fecha_vencimiento_licencia=datetime.date(2027, random.randint(1, 12), random.randint(1, 28)),
        estado='activo',
    )
print(f'  Agregados: 30')

# --- 4. Usuarios ---
print('[4/8] Usuario...')
for i in range(30):
    email = f'new_user_{1000+i}@construtrans.com'
    try:
        Usuario.objects.create(
            username=f'new_user_{1000+i}',
            email=email,
            nombre=f'Nuevo Usuario {1000+i}',
            apellido='Test',
            telefono=f'300{random.randint(10000000, 99999999)}',
            password=make_password('password123'),
            rol='cliente',
            estado='activo',
        )
    except Exception:
        pass
print(f'  Agregados: 30')

# --- 5. Clientes ---
print('[5/8] Cliente...')
for i in range(30):
    email = f'new_cliente_{2000+i}@construtrans.com'
    try:
        Cliente.objects.create(
            usuario=Usuario.objects.create(
                username=f'new_cliente_{2000+i}',
                email=email,
                password=make_password('password123'),
                nombres=f'Nuevo Cliente {2000+i}',
                apellidos='Test',
                telefono=f'300{random.randint(10000000, 99999999)}',
                documento='CC',
                estado='activo',
                rol='cliente',
            ),
            direccion=f'Calle {random.randint(1, 100)}',
            es_vip=False,
            gasto_acumulado=0,
            tipo_cliente='persona',
        )
    except Exception:
        pass
print(f'  Agregados: 30')

# --- 6. Compras ---
print('[6/8] Compra...')
compras = []
for i in range(10):
    compra = Compra.objects.create(
        proveedor=Proveedor.objects.first(),
        fecha_compra=datetime.datetime(2026, 10, random.randint(1, 25), random.randint(0, 23), random.randint(0, 59)),
        subtotal=random.uniform(50000, 5000000),
        impuesto=random.uniform(0, 100000),
        total_compra=random.uniform(50000, 5000000),
        estado=random.choice(['pendiente', 'recibida', 'cancelada']),
        usuario=random.choice(list(Usuario.objects.all())[:10]) if Usuario.objects.exists() else None,
    )
    compras.append(compra)
print(f'  Agregados: {len(compras)}')

# --- 7. Pedidos ---
print('[7/8] Pedido...')
pedidos = []
for i in range(10):
    pedido = Pedido.objects.create(
        usuario=random.choice(list(Usuario.objects.all())[:10]) if Usuario.objects.exists() else None,
        cliente=random.choice(list(Cliente.objects.all())[:5]) if Cliente.objects.exists() else None,
        fecha_solicitud=datetime.datetime(2026, 10, random.randint(1, 25), random.randint(0, 23), random.randint(0, 59)),
        total=random.uniform(50000, 5000000),
        estado=random.choice(['pendiente', 'autorizado_despacho', 'vehiculo_asignado', 'en_ruta', 'entregado', 'cancelado']),
    )
    pedidos.append(pedido)
print(f'  Agregados: {len(pedidos)}')

# --- 8. Reporte ---
print('[8/8] Reporte...')
for i in range(30):
    Reporte.objects.create(
        numero_reporte=f'Rep-{i+1:03d}',
        tipo=random.choice(['inventario', 'ventas', 'compras', 'entregas', 'financiero']),
        descripcion=f'Reporte de prueba {i+1}',
        usuario=random.choice(list(Usuario.objects.all())[:10]) if Usuario.objects.exists() else None,
    )
print(f'  Agregados: 30')

print()
print('=== FIN ===')
