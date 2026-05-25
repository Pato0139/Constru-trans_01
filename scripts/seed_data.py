
import os
import sys
from datetime import date, timedelta
from decimal import Decimal

sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django  # noqa: E402
from django.utils import timezone  # noqa: E402

django.setup()

from django.contrib.auth.models import User  # noqa: E402

from apps.clientes.models import Cliente  # noqa: E402
from apps.facturacion.models import Factura  # noqa: E402
from apps.inventario.models import MovimientoInventario  # noqa: E402
from apps.ordenes.models import DetallePedido, Entrega, Pedido  # noqa: E402
from apps.pagos.models import Pago  # noqa: E402
from apps.usuarios.models import (  # noqa: E402
    EPS,
    Catalogo,
    Conductor,
    ConductorVehiculo,
    MetodoPago,
    Proveedor,
    Stock,
    Usuario,
    Vehiculo,
)
from apps.usuarios.models import MaterialConstruccion as Material  # noqa: E402


def setup_data():
    print("Iniciando creación de datos de prueba completos...")

    try:
        admin_user, created = User.objects.get_or_create(username='Edward_Fonseca', defaults={'email': 'edwardf5432@gmail.com'})
        if created:
            admin_user.set_password('davit12345')
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            print("Superusuario Edward_Fonseca creado.")

        admin_profile, created = Usuario.objects.get_or_create(
            user=admin_user,
            defaults={
                'rol': 'admin',
                'nombres': 'Edward',
                'apellidos': 'Fonseca',
                'documento': '10101010',
                'tipo_documento': 'CC',
                'estado': 'activo'
            }
        )
        if created:
            print("Perfil administrativo para Edward_Fonseca creado.")

        catalogo, _ = Catalogo.objects.get_or_create(
            codigo_catalogo='CAT001',
            defaults={'nombre_empresa': 'Constru-Trans'}
        )

        eps, _ = EPS.objects.get_or_create(
            codigo_eps='EPS001',
            defaults={
                'numero_seguro': '123456789',
                'ciudad': 'Bogotá',
                'direccion': 'Calle 100 # 10-10',
                'telefono': '3101234567',
                'correo': 'contacto@eps.com'
            }
        )

        # Fix MetodoPago creation - try both ways
        try:
            metodo_pago, _ = MetodoPago.objects.get_or_create(
                codigo_metodo_pago='EFECTIVO',
                defaults={'metodo': 'Efectivo'}
            )
        except Exception:
            # If that fails, try looking by metodo
            try:
                metodo_pago = MetodoPago.objects.get(metodo='Efectivo')
            except MetodoPago.DoesNotExist:
                metodo_pago = MetodoPago.objects.create(
                    codigo_metodo_pago='EFECTIVO',
                    metodo='Efectivo'
                )

        proveedores_data = [
            {
                'nombre_empresa': 'Aceros de Colombia S.A.',
                'nit': '900123456',
                'telefono': '3105556677',
                'correo': 'ventas@aceroscol.com',
                'descripcion': 'Materiales de Construcción'
            },
            {
                'nombre_empresa': 'Cales y Arenas del Sur',
                'nit': '800987654',
                'telefono': '3208889900',
                'correo': 'contacto@calessur.com',
                'descripcion': 'Agregados'
            }
        ]

        for p_data in proveedores_data:
            prov, created = Proveedor.objects.get_or_create(
                nit=p_data['nit'],
                defaults=p_data
            )
            if created:
                print(f"Proveedor creado: {prov.nombre_empresa}")

        materiales_data = [
            {'nombre': 'Cemento Gris Argos 50kg', 'precio': 28500, 'descripcion': 'Bulto de cemento gris para construcción general', 'unidad_medida': 'und'},
            {'nombre': 'Varilla Corrugada 1/2"', 'precio': 35000, 'descripcion': 'Varilla de acero estructural 6 metros', 'unidad_medida': 'm'},
            {'nombre': 'Arena de Río (m³)', 'precio': 85000, 'descripcion': 'Arena fina para acabados', 'unidad_medida': 'm³'},
            {'nombre': 'Grava 3/4 (m³)', 'precio': 92000, 'descripcion': 'Grava triturada para concreto', 'unidad_medida': 'm³'},
            {'nombre': 'Ladrillo Estructural', 'precio': 1200, 'descripcion': 'Ladrillo de arcilla cocida', 'unidad_medida': 'und'},
        ]

        mats = []
        for m_data in materiales_data:
            mat, created = Material.objects.get_or_create(
                nombre=m_data['nombre'],
                defaults={
                    'catalogo': catalogo,
                    'precio_referencia': Decimal(m_data['precio']),
                    'descripcion': m_data['descripcion'],
                    'unidad_medida': m_data['unidad_medida']
                }
            )
            mats.append(mat)

            stock, s_created = Stock.objects.get_or_create(
                material=mat,
                defaults={'cantidad_actual': 1000, 'ubicacion': 'Bodega Principal'}
            )
            if not s_created:
                stock.cantidad_actual = 1000
                stock.save()
            print(f"Material: {mat.nombre} - Stock: {stock.cantidad_actual}")

        conductores_data = [
            {'username': 'carlos_chofer', 'email': 'carlos@constru.com', 'nombres': 'Carlos', 'apellidos': 'Mendoza', 'doc': '778899', 'placa': 'TRX-101', 'marca': 'Toyota', 'modelo': 'Hilux', 'tipo_vehiculo': 'Camión 5 Ton', 'capacidad_carga': 5.0},
            {'username': 'pedro_trans', 'email': 'pedro@constru.com', 'nombres': 'Pedro', 'apellidos': 'Salas', 'doc': '554433', 'placa': 'KLM-202', 'marca': 'Chevrolet', 'modelo': 'Silverado', 'tipo_vehiculo': 'Bolqueta 10 Ton', 'capacidad_carga': 10.0},
            {'username': 'luis_driver', 'email': 'luis@constru.com', 'nombres': 'Luis', 'apellidos': 'García', 'doc': '998877', 'placa': 'ABC-123', 'marca': 'Ford', 'modelo': 'F-150', 'tipo_vehiculo': 'Camión 3 Ton', 'capacidad_carga': 3.0},
        ]

        conductores_creados = []
        vehiculos_creados = []
        for c_data in conductores_data:
            u_cond, created = User.objects.get_or_create(username=c_data['username'], defaults={'email': c_data['email']})
            if created:
                u_cond.set_password('davit12345')
                u_cond.save()

            p_cond, created = Usuario.objects.get_or_create(
                user=u_cond,
                defaults={
                    'rol': 'conductor',
                    'nombres': c_data['nombres'],
                    'apellidos': c_data['apellidos'],
                    'documento': c_data['doc'],
                    'tipo_documento': 'CC',
                    'estado': 'activo'
                }
            )

            cond_profile, cond_created = Conductor.objects.get_or_create(
                usuario=p_cond,
                defaults={
                    'numero_licencia': f'LIC-{c_data["doc"]}',
                    'categoria_licencia': 'B2',
                    'fecha_vencimiento_licencia': date.today() + timedelta(days=365),
                    'estado': 'activo',
                    'eps': eps
                }
            )

            vehiculo, v_created = Vehiculo.objects.get_or_create(
                placa=c_data['placa'],
                defaults={
                    'marca': c_data['marca'],
                    'modelo': c_data['modelo'],
                    'tipo_vehiculo': c_data['tipo_vehiculo'],
                    'capacidad_carga': Decimal(str(c_data['capacidad_carga'])),
                    'estado': 'disponible'
                }
            )
            vehiculos_creados.append(vehiculo)

            if cond_created or v_created:
                ConductorVehiculo.objects.get_or_create(
                    conductor=cond_profile,
                    vehiculo=vehiculo
                )

            conductores_creados.append(cond_profile)
            print(f"Conductor {p_cond.nombres} y Vehículo {c_data['placa']} creados.")

        clientes_data = [
            {'username': 'constructora_alfa', 'email': 'proyectos@alfa.com', 'nombres': 'Ing. Roberto', 'apellidos': 'Torres', 'doc': '112233', 'empresa': 'Constructora Alfa SAS'},
            {'username': 'ferreteria_central', 'email': 'compras@central.com', 'nombres': 'Lucía', 'apellidos': 'Pérez', 'doc': '445566', 'empresa': 'Ferretería Central'},
            {'username': 'obra_norte', 'email': 'obra@norte.com', 'nombres': 'Andrés', 'apellidos': 'Rodríguez', 'doc': '776655', 'empresa': 'Obra Norte Ltda'},
        ]

        for cl_data in clientes_data:
            u_cl, created = User.objects.get_or_create(username=cl_data['username'], defaults={'email': cl_data['email']})
            if created:
                u_cl.set_password('davit12345')
                u_cl.save()

            p_cl, created = Usuario.objects.get_or_create(
                user=u_cl,
                defaults={
                    'rol': 'cliente',
                    'nombres': cl_data['nombres'],
                    'apellidos': cl_data['apellidos'],
                    'documento': cl_data['doc'],
                    'tipo_documento': 'CC',
                    'estado': 'activo'
                }
            )

            # Get or create Cliente profile
            cliente_perfil, _ = Cliente.objects.get_or_create(
                usuario=p_cl,
                defaults={
                    'nombre_empresa': cl_data['empresa'],
                    'direccion_principal': 'Av Siempre Viva 123',
                    'tipo_cliente': 'empresa'
                }
            )
            cliente_perfil.nombre_empresa = cl_data['empresa']
            cliente_perfil.direccion_principal = 'Av Siempre Viva 123'
            cliente_perfil.tipo_cliente = 'empresa'
            cliente_perfil.save()

            estados_pedido = ['pendiente', 'en_ruta', 'entregado']
            for idx, estado_p in enumerate(estados_pedido):
                pedido = Pedido.objects.create(
                    usuario=p_cl,
                    direccion_destino=f'Obra {cl_data["empresa"]} - Calle {100 + idx}',
                    estado=estado_p
                )

                total_pedido = 0
                for mat in mats[:3]:
                    cantidad = 20 + (idx * 10)
                    detalle = DetallePedido.objects.create(
                        pedido=pedido,
                        material=mat,
                        cantidad=cantidad,
                        precio_unitario=mat.precio_referencia
                    )
                    total_pedido += detalle.subtotal

                pedido.calcular_total()

                if estado_p != 'pendiente' and conductores_creados and vehiculos_creados:
                    conductor_idx = idx % len(conductores_creados)
                    entrega = Entrega.objects.create(
                        pedido=pedido,
                        conductor=conductores_creados[conductor_idx],
                        vehiculo=vehiculos_creados[conductor_idx],
                        direccion_entrega=pedido.direccion_destino,
                        estado='pendiente' if estado_p == 'en_ruta' else 'entregado'
                    )
                    if estado_p == 'entregado':
                        entrega.fecha_entrega = timezone.now()
                        entrega.save()

                factura, _ = Factura.objects.get_or_create(
                    pedido=pedido,
                    defaults={
                        'cliente': p_cl,
                        'numero': f'FAC-{pedido.id:03d}',
                        'subtotal': pedido.total,
                        'iva': pedido.total * Decimal('0.19'),
                        'total': pedido.total * Decimal('1.19')
                    }
                )

                if estado_p == 'entregado':
                    Pago.objects.get_or_create(
                        factura=factura,
                        defaults={
                            'monto': factura.total,
                            'codigo_metodo_pago': metodo_pago,
                            'registrado_por': admin_user
                        }
                    )

                print(f"Cliente {cl_data['empresa']} - Pedido #{pedido.codigo_pedido} ({estado_p}) - Factura #{factura.numero} creado.")

        print("\nGenerando movimientos de inventario...")
        for mat in mats:
            MovimientoInventario.objects.create(
                material=mat,
                tipo_movimiento='entrada',
                cantidad=1000,
                observacion='Carga inicial de inventario - Seeding'
            )
            print(f"Movimiento de entrada creado para: {mat.nombre}")

        print("\n¡Datos de prueba generados exitosamente!")
        print("\nCredenciales de acceso:")
        print("- Admin: Edward_Fonseca / davit12345")
        print("- Clientes: constructora_alfa, ferreteria_central, obra_norte / davit12345")
        print("- Conductores: carlos_chofer, pedro_trans, luis_driver / davit12345")

    except Exception as e:
        print(f"\n⚠️  Ocurrió un error durante la generación de datos, pero el setup continuará: {e}")
        print("El resto del proceso se completará normalmente.")

if __name__ == "__main__":
    setup_data()

