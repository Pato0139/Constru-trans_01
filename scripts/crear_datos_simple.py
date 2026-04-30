import os
import django
import sys
from decimal import Decimal
from django.utils import timezone

# Configurar Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Usuario, Material, Stock, Vehiculo, Proveedor
from apps.clientes.models import Cliente
from apps.ordenes.models import Orden, DetalleOrden

print("=== Creando datos de prueba ===")

# 1. Superusuario
try:
    admin_user = User.objects.get(username='Edward_Fonseca')
    print("Superusuario ya existe")
except User.DoesNotExist:
    admin_user = User.objects.create_superuser(
        username='Edward_Fonseca',
        email='edwardf5432@gmail.com',
        password='davit12345'
    )
    print("Superusuario Edward_Fonseca creado")

try:
    admin_profile = Usuario.objects.get(user=admin_user)
except Usuario.DoesNotExist:
    admin_profile = Usuario.objects.create(
        user=admin_user,
        rol='admin',
        nombres='Edward',
        apellidos='Fonseca',
        documento='10101010',
        tipo_documento='CC',
        estado='activo'
    )
    print("Perfil admin creado")

# 2. Proveedores
proveedores = [
    {'nombre_empresa': 'Aceros de Colombia S.A.', 'nit': '900123456', 'contacto_nombre': 'Roberto Gómez', 
     'telefono': '3105556677', 'email': 'ventas@aceroscol.com', 'direccion': 'Zona Industrial, Bogotá', 
     'categoria': 'Materiales de Construcción'},
    {'nombre_empresa': 'Cales y Arenas del Sur', 'nit': '800987654', 'contacto_nombre': 'Marta Lucía', 
     'telefono': '3208889900', 'email': 'contacto@calessur.com', 'direccion': 'Vía 40, Barranquilla', 
     'categoria': 'Agregados'}
]

for p_data in proveedores:
    prov, created = Proveedor.objects.get_or_create(nit=p_data['nit'], defaults=p_data)
    if created:
        print(f"Proveedor creado: {prov.nombre_empresa}")

# 3. Materiales
materiales = [
    {'nombre': 'Cemento Gris Argos 50kg', 'tipo': 'Cemento', 'precio': 28500, 
     'descripcion': 'Bulto de cemento gris para construcción general'},
    {'nombre': 'Varilla Corrugada 1/2"', 'tipo': 'Acero', 'precio': 35000, 
     'descripcion': 'Varilla de acero estructural 6 metros'},
    {'nombre': 'Arena de Río (m3)', 'tipo': 'Arena', 'precio': 85000, 
     'descripcion': 'Arena fina para acabados'}
]

mats = []
for m_data in materiales:
    mat, created = Material.objects.get_or_create(nombre=m_data['nombre'], defaults=m_data)
    mats.append(mat)
    if created:
        print(f"Material creado: {mat.nombre}")
    
    stock, s_created = Stock.objects.get_or_create(material=mat, defaults={'cantidad': 1000})
    if s_created:
        print(f"Stock creado para: {mat.nombre}")

# 4. Conductores y Vehículos
conductores = [
    {'username': 'carlos_chofer', 'nombres': 'Carlos', 'apellidos': 'Mendoza', 'doc': '778899', 
     'placa': 'TRX-101', 'tipo': 'Camión 5 Ton'},
    {'username': 'pedro_trans', 'nombres': 'Pedro', 'apellidos': 'Salas', 'doc': '554433', 
     'placa': 'KLM-202', 'tipo': 'Bolqueta 10 Ton'}
]

for c_data in conductores:
    u, created = User.objects.get_or_create(username=c_data['username'])
    if created:
        u.set_password('davit12345')
        u.save()
    
    p, created = Usuario.objects.get_or_create(user=u, defaults={
        'rol': 'conductor', 'nombres': c_data['nombres'], 'apellidos': c_data['apellidos'],
        'documento': c_data['doc'], 'tipo_documento': 'CC', 'estado': 'activo'
    })
    
    v, created = Vehiculo.objects.get_or_create(placa=c_data['placa'], defaults={
        'tipo': c_data['tipo'], 'capacidad': '10 Ton', 'estado': 'disponible', 'conductor': p
    })
    if created:
        print(f"Vehículo creado: {v.placa}")

# 5. Clientes y Órdenes
clientes = [
    {'username': 'constructora_alfa', 'nombres': 'Ing. Roberto', 'apellidos': 'Torres', 
     'doc': '112233', 'empresa': 'Constructora Alfa SAS'},
    {'username': 'ferreteria_central', 'nombres': 'Lucía', 'apellidos': 'Pérez', 
     'doc': '445566', 'empresa': 'Ferretería Central'}
]

for cl_data in clientes:
    u, created = User.objects.get_or_create(username=cl_data['username'])
    if created:
        u.set_password('davit12345')
        u.save()
    
    p, created = Usuario.objects.get_or_create(user=u, defaults={
        'rol': 'cliente', 'nombres': cl_data['nombres'], 'apellidos': cl_data['apellidos'],
        'documento': cl_data['doc'], 'tipo_documento': 'CC', 'estado': 'activo'
    })
    
    cliente_perfil, created = Cliente.objects.get_or_create(usuario=p)
    if created:
        cliente_perfil.razon_social = cl_data['empresa']
        cliente_perfil.save()
        print(f"Cliente creado: {cl_data['empresa']}")
    
    # Crear una orden
    orden = Orden.objects.create(
        cliente=cliente_perfil,
        direccion_destino='Obra Norte - Calle 170',
        estado='pendiente',
        precio=0
    )
    
    total = 0
    for mat in mats:
        det = DetalleOrden.objects.create(
            orden=orden,
            material=mat,
            cantidad=50,
            precio_unitario=mat.precio
        )
        total += mat.precio * 50
    
    orden.precio = total
    orden.save()
    print(f"Orden #{orden.id} creada para {cl_data['empresa']}")

print("\n=== Datos creados exitosamente! ===")
print("Credenciales de superusuario:")
print("  Usuario: Edward_Fonseca")
print("  Contraseña: davit12345")
