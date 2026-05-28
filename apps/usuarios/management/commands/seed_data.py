
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.inventario.models import MovimientoInventario
from apps.ordenes.models import DetallePedido, Entrega, Pedido
from apps.usuarios.models import (
    Conductor,
    ConductorVehiculo,
    EPS,
    MaterialConstruccion,
    Proveedor,
    Stock,
    Usuario,
    Vehiculo,
)


class Command(BaseCommand):
    help = 'Llena la base de datos con datos de prueba'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando creacion de datos de prueba completos...')
        db_alias = 'default'

        # 0. Crear Superusuario Administrador (Edward_Fonseca)
        admin_user, created = User.objects.using(db_alias).get_or_create(username='Edward_Fonseca', defaults={'email': 'edwardf5432@gmail.com'})
        if created:
            admin_user.set_password('davit12345')
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save(using=db_alias)
            self.stdout.write(self.style.SUCCESS('Superusuario Edward_Fonseca creado.'))

        admin_profile, created = Usuario.objects.using(db_alias).get_or_create(
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
            self.stdout.write(self.style.SUCCESS('Perfil administrativo para Edward_Fonseca creado.'))

        # 1. Crear EPS (required for Conductor)
        eps, _ = EPS.objects.using(db_alias).get_or_create(
            codigo_eps='EPS001',
            defaults={
                'numero_seguro': '123456789',
                'ciudad': 'Bogota',
                'direccion': 'Calle 100 # 10-10',
                'telefono': '3101234567',
                'correo': 'contacto@eps.com'
            }
        )

        # 2. Crear Proveedores
        proveedores_data = [
            {
                'nombre_empresa': 'Aceros de Colombia S.A.',
                'nit': '900123456',
                'telefono': '3105556677',
                'correo': 'ventas@aceroscol.com',
                'descripcion': 'Proveedor de materiales de acero'
            },
            {
                'nombre_empresa': 'Cales y Arenas del Sur',
                'nit': '800987654',
                'telefono': '3208889900',
                'correo': 'contacto@calessur.com',
                'descripcion': 'Proveedor de arenas y gravas'
            }
        ]

        for p_data in proveedores_data:
            prov, created = Proveedor.objects.using(db_alias).get_or_create(
                nit=p_data['nit'],
                defaults=p_data
            )
            if created:
                self.stdout.write(f'Proveedor creado: {prov.nombre_empresa}')

        # 3. Crear Materiales y Stock
        materiales_data = [
            {'nombre': 'Cemento Gris Argos 50kg', 'unidad_medida': 'Bulto', 'precio_referencia': 28500, 'descripcion': 'Bulto de cemento gris para construccion general'},
            {'nombre': 'Varilla Corrugada 1/2"', 'unidad_medida': 'Unidad', 'precio_referencia': 35000, 'descripcion': 'Varilla de acero estructural 6 metros'},
            {'nombre': 'Arena de Rio (m3)', 'unidad_medida': 'm3', 'precio_referencia': 85000, 'descripcion': 'Arena fina para acabados'},
            {'nombre': 'Grava 3/4 (m3)', 'unidad_medida': 'm3', 'precio_referencia': 92000, 'descripcion': 'Grava triturada para concreto'},
            {'nombre': 'Ladrillo Estructural', 'unidad_medida': 'Unidad', 'precio_referencia': 1200, 'descripcion': 'Ladrillo de arcilla cocida'},
        ]

        mats = []
        for m_data in materiales_data:
            mat, created = MaterialConstruccion.objects.using(db_alias).get_or_create(
                nombre=m_data['nombre'],
                defaults=m_data
            )
            mats.append(mat)

            stock, s_created = Stock.objects.using(db_alias).get_or_create(
                material=mat,
                defaults={'cantidad_actual': 1000, 'stock_minimo': 100, 'ubicacion': 'Bodega Principal'}
            )
            if not s_created:
                stock.cantidad_actual = 1000
                stock.save(using=db_alias)
            self.stdout.write(f'Material: {mat.nombre} - Stock: {stock.cantidad_actual}')

        # 4. Crear Conductores y Vehiculos
        conductores_data = [
            {'username': 'carlos_chofer', 'email': 'carlos@constru.com', 'nombres': 'Carlos', 'apellidos': 'Mendoza', 'doc': '778899', 'placa': 'TRX-101', 'marca': 'Toyota', 'modelo': 'Hilux', 'tipo': 'Camion 5 Ton', 'capacidad': 5.0},
            {'username': 'pedro_trans', 'email': 'pedro@constru.com', 'nombres': 'Pedro', 'apellidos': 'Salas', 'doc': '554433', 'placa': 'KLM-202', 'marca': 'Chevrolet', 'modelo': 'Silverado', 'tipo': 'Bolqueta 10 Ton', 'capacidad': 10.0},
            {'username': 'luis_driver', 'email': 'luis@constru.com', 'nombres': 'Luis', 'apellidos': 'Garcia', 'doc': '998877', 'placa': 'ABC-123', 'marca': 'Ford', 'modelo': 'F-150', 'tipo': 'Camion 3 Ton', 'capacidad': 3.0},
        ]

        conductores_creados = []
        vehiculos_creados = []
        for c_data in conductores_data:
            u_cond, created = User.objects.using(db_alias).get_or_create(username=c_data['username'], defaults={'email': c_data['email']})
            if created:
                u_cond.set_password('davit12345')
                u_cond.save(using=db_alias)

            p_cond, created = Usuario.objects.using(db_alias).get_or_create(
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

            cond_profile, cond_created = Conductor.objects.using(db_alias).get_or_create(
                usuario=p_cond,
                defaults={
                    'numero_licencia': f'LIC-{c_data["doc"]}',
                    'categoria_licencia': 'C2',
                    'fecha_vencimiento_licencia': date.today() + timedelta(days=365),
                    'estado': 'activo',
                    'eps': eps
                }
            )

            vehiculo, v_created = Vehiculo.objects.using(db_alias).get_or_create(
                placa=c_data['placa'],
                defaults={
                    'marca': c_data['marca'],
                    'modelo': c_data['modelo'],
                    'tipo_vehiculo': c_data['tipo'],
                    'capacidad_carga': c_data['capacidad'],
                    'estado': 'disponible'
                }
            )
            vehiculos_creados.append(vehiculo)
            
            # Create ConductorVehiculo relationship
            ConductorVehiculo.objects.using(db_alias).get_or_create(
                conductor=cond_profile,
                vehiculo=vehiculo
            )
            
            conductores_creados.append(cond_profile)
            self.stdout.write(f'Conductor {p_cond.nombres} y Vehiculo {c_data["placa"]} creados.')

        # 5. Crear Clientes y Pedidos
        clientes_data = [
            {'username': 'constructora_alfa', 'email': 'proyectos@alfa.com', 'nombres': 'Ing. Roberto', 'apellidos': 'Torres', 'doc': '112233', 'empresa': 'Constructora Alfa SAS'},
            {'username': 'ferreteria_central', 'email': 'compras@central.com', 'nombres': 'Lucia', 'apellidos': 'Perez', 'doc': '445566', 'empresa': 'Ferreteria Central'},
            {'username': 'obra_norte', 'email': 'obra@norte.com', 'nombres': 'Andres', 'apellidos': 'Rodriguez', 'doc': '776655', 'empresa': 'Obra Norte Ltda'},
        ]

        for cl_data in clientes_data:
            u_cl, created = User.objects.using(db_alias).get_or_create(username=cl_data['username'], defaults={'email': cl_data['email']})
            if created:
                u_cl.set_password('davit12345')
                u_cl.save(using=db_alias)

            p_cl, created = Usuario.objects.using(db_alias).get_or_create(
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

            cliente_perfil, _ = Cliente.objects.using(db_alias).get_or_create(
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
            cliente_perfil.save(using=db_alias)

            estados_pedido = ['pendiente', 'en_ruta', 'entregado']
            for idx, estado_p in enumerate(estados_pedido):
                # Create Pedido with both usuario and cliente fields
                pedido = Pedido.objects.using(db_alias).create(
                    usuario=p_cl,
                    cliente=p_cl,
                    direccion_destino=f'Obra {cl_data["empresa"]} - Calle {100 + idx}',
                    estado=estado_p
                )

                total_pedido = 0
                for mat in mats[:3]:
                    cantidad = 20 + (idx * 10)
                    detalle = DetallePedido.objects.using(db_alias).create(
                        pedido=pedido,
                        material=mat,
                        cantidad=cantidad,
                        precio_unitario=mat.precio_referencia
                    )
                    total_pedido += detalle.subtotal

                # Need to refresh pedido from DB to calculate total correctly
                pedido.refresh_from_db()
                pedido.calcular_total()

                if estado_p != 'pendiente' and conductores_creados and vehiculos_creados:
                    conductor_idx = idx % len(conductores_creados)
                    entrega = Entrega.objects.using(db_alias).create(
                        pedido=pedido,
                        conductor=conductores_creados[conductor_idx],
                        vehiculo=vehiculos_creados[conductor_idx],
                        direccion_entrega=pedido.direccion_destino,
                        estado='pendiente' if estado_p == 'en_ruta' else 'entregado'
                    )
                    if estado_p == 'entregado':
                        entrega.fecha_entrega = timezone.now()
                        entrega.save(using=db_alias)

                self.stdout.write(f'Cliente {cl_data["empresa"]} - Pedido #{pedido.codigo_pedido} ({estado_p}) creado.')

        # 6. Crear Movimientos de Inventario
        self.stdout.write('\nGenerando movimientos de inventario...')
        for mat in mats:
            MovimientoInventario.objects.using(db_alias).create(
                material=mat,
                tipo_movimiento='entrada',
                cantidad=1000,
                observacion='Carga inicial de inventario - Seeding'
            )
            self.stdout.write(f'Movimiento de entrada creado para: {mat.nombre}')

        self.stdout.write(self.style.SUCCESS('\nDatos de prueba generados exitosamente!'))
        self.stdout.write('\nCredenciales de acceso:')
        self.stdout.write('- Admin: Edward_Fonseca / davit12345')
        self.stdout.write('- Clientes: constructora_alfa, ferreteria_central, obra_norte / davit12345')
        self.stdout.write('- Conductores: carlos_chofer, pedro_trans, luis_driver / davit12345')
