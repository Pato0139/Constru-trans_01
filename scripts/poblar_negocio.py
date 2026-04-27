
import os
import sys
import django
import random
from pathlib import Path
from decimal import Decimal
from django.utils import timezone

# Añadir el directorio raíz al sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from apps.usuarios.models import Usuario, Material, Proveedor, Vehiculo, Stock
from apps.compras.models import Compra, DetalleCompra
from apps.ordenes.models import Orden, Entrega
from apps.facturacion.models import Factura
from apps.pagos.models import Pago

def populate_business_data():
    print("--- Poblando datos de negocio (Proveedores, Compras, Vehículos, Facturas) ---")

    # 1. Crear Proveedores
    proveedores_data = [
        ('Cemex Colombia', '800.032.124-5', 'Juan Castro', '3101234567', 'ventas@cemex.com', 'Zona Industrial Bogotá', 'Cemento y Concreto'),
        ('Aceros Diaco', '900.555.222-1', 'Marta Herrera', '3209876543', 'compras@diaco.com', 'Tuta, Boyacá', 'Acero y Hierro'),
        ('Holcim', '860.000.123-9', 'Pedro Picapiedra', '3001112233', 'contacto@holcim.co', 'Sogamoso', 'Agregados y Cemento'),
    ]

    for nom, nit, cont, tel, email, dir, cat in proveedores_data:
        prov, created = Proveedor.objects.get_or_create(
            nit=nit,
            defaults={
                'nombre_empresa': nom,
                'contacto_nombre': cont,
                'telefono': tel,
                'email': email,
                'direccion': dir,
                'categoria': cat,
                'sincronizado': False
            }
        )
        if created: print(f"Proveedor creado: {nom}")

    # 2. Crear Materiales y Stock
    materiales_data = [
        ('Cemento Gris 50kg', 'Agregados', 'Bulto de cemento tipo I', 28500.00, 500),
        ('Varilla 1/2 pulgada', 'Acero', 'Varilla corrugada de 6 metros', 45000.00, 200),
        ('Arena de Río', 'Agregados', 'Metro cúbico de arena lavada', 65000.00, 50),
    ]

    for nom, tipo, desc, prec, cant in materiales_data:
        mat, created = Material.objects.get_or_create(
            nombre=nom,
            defaults={
                'tipo': tipo,
                'descripcion': desc,
                'precio': prec,
                'sincronizado': False
            }
        )
        if created:
            Stock.objects.get_or_create(material=mat, defaults={'cantidad': cant})
            print(f"Material y Stock creado: {nom}")

    # 3. Crear Vehículos con nuevos estados
    vehiculos_data = [
        ('HGE312', 'Bolqueta', '180', 'en_ruta', 'propio'),
        ('JIK456', 'Camión Sencillo', '120', 'alquilado', 'alquilado'),
        ('KLO789', 'Mixer Concreto', '250', 'disponible', 'propio'),
        ('OLD999', 'Camioneta Estacas', '60', 'desactivado', 'propio'),
    ]

    for placa, tipo, cap, est, adq in vehiculos_data:
        veh, created = Vehiculo.objects.get_or_create(
            placa=placa,
            defaults={
                'tipo': tipo,
                'capacidad': cap,
                'estado': est,
                'tipo_adquisicion': adq,
                'sincronizado': False
            }
        )
        if created: print(f"Vehículo creado: {placa} ({est})")

    # 4. Crear Compras (Movimientos de dinero)
    prov = Proveedor.objects.first()
    mat = Material.objects.first()
    if prov and mat:
        compra = Compra.objects.create(
            proveedor=prov,
            estado='recibida',
            total=Decimal('1425000.00'),
            observaciones='Compra inicial de stock',
            sincronizado=False
        )
        DetalleCompra.objects.create(
            compra=compra,
            material=mat,
            cantidad=50,
            precio_unitario=Decimal('28500.00')
        )
        print(f"Compra de stock registrada: {compra.numero_orden}")

    # 5. Crear Órdenes, Entregas, Facturas y Pagos (Flujo Completo)
    # Necesitamos un cliente
    cliente_user = Usuario.objects.filter(rol='cliente').first()
    conductor_user = Usuario.objects.filter(rol='conductor').first()
    
    if cliente_user:
        # Orden Entregada y Pagada
        orden = Orden.objects.create(
            cliente=cliente_user,
            estado='completada',
            total=Decimal('250000.00'),
            sincronizado=False
        )
        
        # Entrega
        Entrega.objects.create(
            orden=orden,
            vehiculo=Vehiculo.objects.first(),
            conductor=conductor_user,
            estado='entregado',
            sincronizado=False
        )

        # Factura
        factura = Factura.objects.create(
            orden=orden,
            cliente=cliente_user,
            total=Decimal('250000.00'),
            estado='pagada',
            sincronizado=False
        )

        # Pago
        Pago.objects.create(
            factura=factura,
            monto=Decimal('250000.00'),
            metodo='transferencia',
            referencia='PAGO-TEST-001',
            registrado_por=User.objects.first(),
            sincronizado=False
        )
        print(f"Flujo completo registrado: Orden {orden.id} -> Factura {factura.id} (PAGADA)")

if __name__ == "__main__":
    populate_business_data()
    print("--- Proceso completado exitosamente ---")
