"""
Script para poblar la base de datos con datos temporales de prueba.
Ejecuta: python manage.py shell < seed_data.py
O mejor: crea un management command.
"""

import os
import sys
from datetime import timedelta
from decimal import Decimal

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from catalogo.models import Catalogo, Marca, MaterialConstruccion, UnidadMedida
from clientes.models import Cliente as ClienteModel
from django.contrib.auth import get_user_model
from django.utils import timezone
from logistica.models import ConductorVehiculo, Entrega, Vehiculo
from pedidos.models import DetallePedido, Pago, Pedido
from usuarios.models import EPS, Conductor

User = get_user_model()


def seed():
    print("=" * 60)
    print("  Poblando base de datos con datos temporales...")
    print("=" * 60)

    # 1. Crear EPS
    print("\n[1/8] Creando EPS...")
    eps, _ = EPS.objects.get_or_create(
        codigo_eps="EPS001",
        defaults={
            "numero_seguro": "1234567890",
            "ciudad": "Tunja",
            "direccion": "Calle 10 #5-20",
            "telefono": "3001234567",
            "correo": "eps@ejemplo.com",
        },
    )
    print(f"  ✅ EPS: {eps.codigo_eps}")

    # 2. Crear usuarios
    print("\n[2/8] Creando usuarios...")

    # Admin (crear sin superuser para evitar signal, luego actualizar)
    admin, _ = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@constru-trans.com",
            "nombres": "Admin",
            "apellidos": "Sistema",
            "documento": "1000000001",
            "rol": "admin",
            "tipo_documento": "CC",
            "estado": "activo",
            "is_staff": False,
            "is_superuser": False,
        },
    )
    admin.set_password("admin123")
    admin.save()
    # Hacer superuser directamente en BD para evitar el signal
    User.objects.filter(pk=admin.pk).update(is_staff=True, is_superuser=True)
    admin.refresh_from_db()
    print(f"  ✅ Admin: {admin.username} / admin123")

    # Clientes
    clientes_users = []
    for i in range(1, 6):
        user, _ = User.objects.get_or_create(
            username=f"cliente{i}",
            defaults={
                "email": f"cliente{i}@ejemplo.com",
                "nombres": f"Cliente {i}",
                "apellidos": f"Pérez {i}",
                "documento": f"100000000{i + 1}",
                "rol": "cliente",
                "tipo_documento": "CC",
                "estado": "activo",
            },
        )
        user.set_password("cliente123")
        user.save()
        clientes_users.append(user)
        print(f"  ✅ Cliente: {user.username} / cliente123")

    # Conductores
    conductores_users = []
    for i in range(1, 4):
        user, _ = User.objects.get_or_create(
            username=f"conductor{i}",
            defaults={
                "email": f"conductor{i}@ejemplo.com",
                "nombres": f"Conductor {i}",
                "apellidos": f"Gómez {i}",
                "documento": f"200000000{i}",
                "rol": "conductor",
                "tipo_documento": "CC",
                "estado": "activo",
            },
        )
        user.set_password("conductor123")
        user.save()
        conductores_users.append(user)
        print(f"  ✅ Conductor: {user.username} / conductor123")

    # 3. Crear perfiles de cliente
    print("\n[3/8] Creando perfiles de cliente...")
    for i, user in enumerate(clientes_users, 1):
        cliente, _ = ClienteModel.objects.get_or_create(
            usuario=user,
            defaults={
                "direccion_principal": f"Carrera {i} #10-{i}0, Tunja",
                "direccion": f"Carrera {i} #10-{i}0, Tunja",
                "tipo_cliente": "persona" if i <= 3 else "empresa",
                "es_vip": i == 1,
                "gasto_acumulado": Decimal(f"{i * 500000}"),
            },
        )
        print(f"  ✅ Perfil cliente: {user.nombres}")

    # 4. Crear perfiles de conductor
    print("\n[4/8] Creando perfiles de conductor...")
    for i, user in enumerate(conductores_users, 1):
        conductor, _ = Conductor.objects.get_or_create(
            usuario=user,
            defaults={
                "numero_licencia": f"LIC-2024-{i:04d}",
                "categoria_licencia": "B1",
                "fecha_vencimiento_licencia": timezone.now().date() + timedelta(days=365),
                "estado": "activo",
                "eps": eps,
            },
        )
        print(f"  ✅ Perfil conductor: {user.nombres}")

    # 5. Crear catálogo y materiales
    print("\n[5/8] Creando catálogo y materiales...")

    catalogo, _ = Catalogo.objects.get_or_create(
        codigo_catalogo="CAT001", defaults={"nombre_empresa": "Constru-Trans S.A.S."}
    )

    # Unidades de medida
    unidades = [
        ("UND", "Unidad", "Und."),
        ("KG", "Kilogramo", "Kg"),
        ("MT", "Metro", "m"),
        ("M2", "Metro Cuadrado", "m²"),
        ("M3", "Metro Cúbico", "m³"),
        ("LT", "Litro", "L"),
        ("TON", "Tonelada", "Ton"),
    ]
    for codigo, nombre, abreviatura in unidades:
        UnidadMedida.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "abreviatura": abreviatura}
        )

    # Marcas
    marcas = ["Argos", "Cemex", "Holcim", "Eternit", "Corona"]
    for nombre in marcas:
        Marca.objects.get_or_create(nombre=nombre)

    # Materiales
    materiales_data = [
        ("Cemento gris bolsa 50kg", "KG", "Argos", 35000),
        ("Arena lavada m³", "M3", "Cemex", 45000),
        ("Gravilla 3/4 m³", "M3", "Holcim", 55000),
        ("Ladrillo tolete 12x24x6 cm", "UND", "Corona", 1200),
        ("Bloque de concreto 10x20x40 cm", "UND", "Corona", 2500),
        ('Varilla corrugada 3/8" x 6m', "UND", "Eternit", 18000),
        ('Varilla corrugada 1/2" x 6m', "UND", "Eternit", 28000),
        ("Alambre recocido No. 18 kg", "KG", "Eternit", 8500),
        ("Teja ondulada fibrocemento 2.4m", "UND", "Eternit", 22000),
        ("Pintura vinilo blanco galón", "LT", "Corona", 45000),
    ]

    materiales = []
    for nombre, unidad_cod, marca_nombre, precio in materiales_data:
        unidad = UnidadMedida.objects.get(codigo=unidad_cod)
        marca = Marca.objects.get(nombre=marca_nombre)
        material, _ = MaterialConstruccion.objects.get_or_create(
            nombre=nombre,
            defaults={
                "catalogo": catalogo,
                "marca": marca,
                "unidad_medida": unidad,
                "descripcion": f"{nombre} de alta calidad para construcción",
                "precio_referencia": Decimal(precio),
                "activo": True,
            },
        )
        materiales.append(material)
        print(f"  ✅ Material: {material.nombre}")

    # 6. Crear vehículos
    print("\n[6/8] Creando vehículos...")
    vehiculos_data = [
        ("ABC123", "Chevrolet", "NHR", "Camión 3.5T", 3500),
        ("DEF456", "Hyundai", "HR", "Camión 5T", 5000),
        ("GHI789", "Ford", "Cargo", "Camión 8T", 8000),
    ]

    vehiculos = []
    for placa, marca, modelo, tipo, capacidad in vehiculos_data:
        vehiculo, _ = Vehiculo.objects.get_or_create(
            placa=placa,
            defaults={
                "catalogo": catalogo,
                "marca": marca,
                "modelo": modelo,
                "tipo_vehiculo": tipo,
                "capacidad_carga": Decimal(capacidad),
                "estado": "disponible",
            },
        )
        vehiculos.append(vehiculo)
        print(f"  ✅ Vehículo: {vehiculo.placa}")

    # Asignar vehículos a conductores
    for i, conductor_user in enumerate(conductores_users):
        conductor = Conductor.objects.get(usuario=conductor_user)
        ConductorVehiculo.objects.get_or_create(
            conductor=conductor,
            vehiculo=vehiculos[i],
            defaults={"fecha_asignacion": timezone.now()},
        )
        print(f"  ✅ Asignación: {conductor_user.nombres} → {vehiculos[i].placa}")

    # 7. Crear pedidos con diferentes estados
    print("\n[7/8] Creando pedidos...")

    estados_pedidos = [
        "pendiente",
        "autorizado_despacho",
        "vehiculo_asignado",
        "en_ruta",
        "entregado",
        "cancelado",
    ]

    pedidos = []
    for i, estado in enumerate(estados_pedidos, 1):
        cliente_user = clientes_users[i % len(clientes_users)]
        cliente = ClienteModel.objects.get(usuario=cliente_user)

        pedido, created = Pedido.objects.get_or_create(
            codigo_pedido=i,
            defaults={
                "catalogo": catalogo,
                "usuario": cliente_user,
                "cliente": cliente,
                "estado": estado,
                "direccion_origen": "Bodega Central Constru-Trans",
                "direccion_destino": cliente.direccion_principal,
                "fecha_entrega_programada": timezone.now() + timedelta(days=7),
                "total": 0,
                "precio": 0,
            },
        )

        if created:
            # Agregar detalles al pedido
            for j, material in enumerate(materiales[:3], 1):
                cantidad = j * 5
                DetallePedido.objects.create(
                    pedido=pedido,
                    material=material,
                    cantidad=cantidad,
                    precio_unitario=material.precio_referencia,
                )

            # Calcular total
            pedido.calcular_total()

            # Si está en ruta o entregado, asignar conductor
            conductor = None
            if estado in ["en_ruta", "entregado", "vehiculo_asignado"]:
                conductor = Conductor.objects.get(usuario=conductores_users[0])
                pedido.conductor = conductor
                pedido.conductor_usuario_legacy = conductores_users[0]
                pedido.save()

            # Si está entregado, crear entrega
            if estado == "entregado" and conductor:
                Entrega.objects.create(
                    pedido=pedido,
                    conductor=conductor,
                    vehiculo=vehiculos[0] if vehiculos else None,
                    estado="entregado",
                    direccion_entrega=pedido.direccion_destino,
                    fecha_salida=timezone.now() - timedelta(days=2),
                    fecha_entrega=timezone.now() - timedelta(days=1),
                )
                print(f"  ✅ Entrega creada para pedido {pedido.codigo_pedido}")

        pedidos.append(pedido)
        print(
            f"  ✅ Pedido {pedido.codigo_pedido}: {pedido.get_estado_display()} - ${pedido.total}"
        )

    # 8. Crear pagos
    print("\n[8/8] Creando pagos...")
    for i, pedido in enumerate(pedidos[:4], 1):
        pago, created = Pago.objects.get_or_create(
            pedido=pedido,
            defaults={
                "metodo": "nequi" if i % 2 == 0 else "daviplata",
                "monto": pedido.total,
                "estado": "aprobado" if i <= 2 else "pendiente",
            },
        )
        if created:
            print(f"  ✅ Pago pedido {pedido.codigo_pedido}: {pago.get_estado_display()}")

    print("\n" + "=" * 60)
    print("  ✅ Datos temporales creados exitosamente!")
    print("=" * 60)
    print("\nCredenciales de acceso:")
    print("  Admin:    admin / admin123")
    print("  Cliente:  cliente1 / cliente123")
    print("  Conductor: conductor1 / conductor123")
    print("\nPedidos creados con estados:")
    for pedido in pedidos:
        print(f"  - Pedido {pedido.codigo_pedido}: {pedido.get_estado_display()}")


if __name__ == "__main__":
    seed()
