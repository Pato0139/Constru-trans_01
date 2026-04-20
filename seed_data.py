import os
import django
import sys

# Configurar Django
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Usuario, Material, Stock, Vehiculo
from apps.ordenes.models import Orden, DetalleOrden
from apps.inventario.models import MovimientoInventario
from django.utils import timezone
from decimal import Decimal

def setup_data():
    print("Iniciando creación de datos de prueba...")
    
    # 1. Crear Materiales si no existen
    materiales_data = [
        {'nombre': 'Cemento Gris Argos', 'tipo': 'Cemento', 'precio': 28500, 'descripcion': 'Bulto de cemento 50kg'},
        {'nombre': 'Arena de Rio', 'tipo': 'Arena', 'precio': 85000, 'descripcion': 'Metro cubico de arena fina'},
        {'nombre': 'Grava 3/4', 'tipo': 'Grava', 'precio': 92000, 'descripcion': 'Grava para concreto'},
    ]
    
    mats = []
    for m_data in materiales_data:
        mat, created = Material.objects.get_or_create(
            nombre=m_data['nombre'],
            defaults={'tipo': m_data['tipo'], 'precio': Decimal(m_data['precio']), 'descripcion': m_data['descripcion']}
        )
        mats.append(mat)
        # Asegurar stock
        stock, s_created = Stock.objects.get_or_create(material=mat)
        stock.cantidad = 500
        stock.save()
        print(f"Material: {mat.nombre} - Stock: {stock.cantidad}")

    # 2. Crear Usuarios (Cliente y Conductor)
    # Cliente
    u_cliente, created = User.objects.get_or_create(username='cliente_test', email='cliente@test.com')
    if created:
        u_cliente.set_password('pass123')
        u_cliente.save()
    p_cliente, created = Usuario.objects.get_or_create(
        user=u_cliente,
        defaults={'rol': 'cliente', 'nombres': 'Juan', 'apellidos': 'Perez', 'documento': '12345', 'tipo_documento': 'CC'}
    )

    # Conductor
    u_conductor, created = User.objects.get_or_create(username='conductor_test', email='cond@test.com')
    if created:
        u_conductor.set_password('pass123')
        u_conductor.save()
    p_conductor, created = Usuario.objects.get_or_create(
        user=u_conductor,
        defaults={'rol': 'conductor', 'nombres': 'Carlos', 'apellidos': 'Ruedas', 'documento': '67890', 'tipo_documento': 'CC'}
    )

    # 3. Crear Vehículo y asignar a conductor
    vehiculo, created = Vehiculo.objects.get_or_create(
        placa='TRX-789',
        defaults={'tipo': 'Bolqueta', 'capacidad': '10 Ton', 'estado': 'disponible', 'conductor': p_conductor}
    )
    print(f"Vehículo {vehiculo.placa} asignado a {p_conductor}")

    # 4. Generar un Pedido y Factura (Orden completada)
    orden = Orden.objects.create(
        cliente=p_cliente,
        direccion_destino='Calle 100 # 15-20, Bogotá',
        estado='entregado',
        precio=0, # Se calcula abajo
        fecha_entrega_real=timezone.now()
    )
    
    total = 0
    # Agregar detalles (Incluir Grava)
    for m in mats: # Ahora incluimos los 3 materiales (Cemento, Arena, Grava)
        cant = 17 if 'Cemento' in m.nombre else (10 if 'Arena' in m.nombre else 5)
        DetalleOrden.objects.create(
            orden=orden,
            material=m,
            cantidad=cant,
            precio_unitario=m.precio
        )
        total += m.precio * cant
        # Descontar stock
        stock = m.stock_info
        stock.cantidad -= cant
        stock.save()
        
    orden.precio = total
    orden.save()
    print(f"Pedido #{orden.id} creado para {p_cliente} - Total: ${orden.precio}")

    # 5. Registrar una Entrada de Inventario (Simulación)
    mat_refill = mats[2]
    cantidad_entrada = 100
    stock_refill = mat_refill.stock_info
    stock_refill.cantidad += cantidad_entrada
    stock_refill.save()
    
    MovimientoInventario.objects.create(
        material=mat_refill,
        tipo='entrada',
        cantidad=cantidad_entrada,
        motivo='Reposición de inventario semanal',
        usuario=u_cliente # Usamos cualquier user para el test
    )
    print(f"Entrada de inventario: {cantidad_entrada} unidades de {mat_refill.nombre}")

if __name__ == "__main__":
    setup_data()
