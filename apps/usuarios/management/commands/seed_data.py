
from datetime import date

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.inventario.models import MovimientoInventario
from apps.ordenes.models import DetallePedido, Entrega, Pedido
from apps.usuarios.models import (
    Conductor,
    MaterialConstruccion,
    Proveedor,
    Stock,
    Usuario,
    Vehiculo,
)


class Command(BaseCommand):
    help = 'Llena la base de datos con datos de prueba'

    def handle(self, *args, **options):
        self.stdout.write('Iniciando creación de datos de prueba completos...')

        # 0. Crear Superusuario Administrador (Edward_Fonseca)
        admin_user, created = User.objects.get_or_create(username='Edward_Fonseca', defaults={'email': 'edwardf5432@gmail.com'})
        if created:
            admin_user.set_password('davit12345')
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Superusuario Edward_Fonseca creado.'))

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
            self.stdout.write(self.style.SUCCESS('Perfil administrativo para Edward_Fonseca creado.'))

        # 1. Crear Proveedores
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
            prov, created = Proveedor.objects.get_or_create(
                nit=p_data['nit'],
                defaults=p_data
            )
            if created:
                self.stdout.write(f'Proveedor creado: {prov.nombre_empresa}')

        # 2. Crear Materiales y Stock
        materiales_data = [
            {'nombre': 'Cemento Gris Argos 50kg', 'unidad_medida': 'Bulto', 'precio_referencia': 28500, 'descripcion': 'Bulto de cemento gris para construcción general'},
            {'nombre': 'Varilla Corrugada 1/2"', 'unidad_medida': 'Unidad', 'precio_referencia': 35000, 'descripcion': 'Varilla de acero estructural 6 metros'},
            {'nombre': 'Arena de Río (m³)', 'unidad_medida': 'm³', 'precio_referencia': 85000, 'descripcion': 'Arena fina para acabados'},
            {'nombre': 'Grava 3/4 (m³)', 'unidad_medida': 'm³', 'precio_referencia': 92000, 'descripcion': 'Grava triturada para concreto'},
            {'nombre': 'Ladrillo Estructural', 'unidad_medida': 'Unidad', 'precio_referencia': 1200, 'descripcion': 'Ladrillo de arcilla cocida'},
        ]

        mats = []
        for m_data in materiales_data:
            mat, created = MaterialConstruccion.objects.get_or_create(
                nombre=m_data['nombre'],
                defaults=m_data
            )
            mats.append(mat)

            stock, s_created = Stock.objects.get_or_create(
                material=mat,
                defaults={'cantidad_actual': 1000, 'stock_minimo': 100}
            )
            if not s_created:
                stock.cantidad_actual = 1000
                stock.save()
            self.stdout.write(f'Material: {mat.nombre} - Stock: {stock.cantidad_actual}')

        # 3. Crear Conductores y Vehículos
        conductores_data = [
            {'username': 'carlos_chofer', 'email': 'carlos@constru.com', 'nombres': 'Carlos', 'apellidos': 'Mendoza', 'doc': '778899', 'placa': 'TRX-101', 'marca': 'Toyota', 'modelo': 'Hilux', 'tipo': 'Camión 5 Ton'},
            {'username': 'pedro_trans', 'email': 'pedro@constru.com', 'nombres': 'Pedro', 'apellidos': 'Salas', 'doc': '554433', 'placa': 'KLM-202', 'marca': 'Chevrolet', 'modelo': 'Silverado', 'tipo': 'Bolqueta 10 Ton'},
            {'username': 'luis_driver', 'email': 'luis@constru.com', 'nombres': 'Luis', 'apellidos': 'García', 'doc': '998877', 'placa': 'ABC-123', 'marca': 'Ford', 'modelo': 'F-150', 'tipo': 'Camión 3 Ton'},
        ]

        conductores_creados = []
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
                    'categoria_licencia': 'C2',
                    'fecha_vencimiento_licencia': date(2030, 12, 31),
                    'estado': 'activo'
                }
            )

            vehiculo, v_created = Vehiculo.objects.get_or_create(
                placa=c_data['placa'],
                defaults={
                    'marca': c_data['marca'],
                    'modelo': c_data['modelo'],
                    'tipo_vehiculo': c_data['tipo'],
                    'capacidad_carga': 10,
                    'estado': 'disponible'
                }
            )
            conductores_creados.append(cond_profile)
            self.stdout.write(f'Conductor {p_cond.nombres} y Vehículo {c_data["placa"]} creados.')

        # 4. Crear Clientes y Pedidos
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

            cliente_perfil = Cliente.objects.get(usuario=p_cl)
            cliente_perfil.nombre_empresa = cl_data['empresa']
            cliente_perfil.direccion_principal = 'Av Siempre Viva 123'
            cliente_perfil.tipo_cliente = 'empresa'
            cliente_perfil.save()

            estados_pedido = ['pendiente', 'pendiente', 'en_ruta', 'entregado']
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

                if estado_p != 'pendiente' and conductores_creados:
                    conductor_idx = idx % len(conductores_creados)
                    vehiculo = None
                    for v in Vehiculo.objects.all():
                        vehiculo = v
                        break
                    if vehiculo:
                        entrega = Entrega.objects.create(
                            pedido=pedido,
                            conductor=conductores_creados[conductor_idx],
                            vehiculo=vehiculo,
                            direccion_entrega=pedido.direccion_destino,
                            estado='pendiente' if estado_p == 'en_ruta' else 'entregado'
                        )
                        if estado_p == 'entregado':
                            entrega.fecha_entrega = timezone.now()
                            entrega.save()

                self.stdout.write(f'Cliente {cl_data["empresa"]} - Pedido #{pedido.codigo_pedido} ({estado_p}) creado.')

        # 5. Crear Movimientos de Inventario
        self.stdout.write('\nGenerando movimientos de inventario...')
        for mat in mats:
            MovimientoInventario.objects.create(
                material=mat,
                tipo='entrada',
                cantidad=1000,
                motivo='Carga inicial de inventario - Seeding',
                referencia_id=0
            )
            self.stdout.write(f'Movimiento de entrada creado para: {mat.nombre}')

        self.stdout.write(self.style.SUCCESS('\n¡Datos de prueba generados exitosamente!'))
        self.stdout.write('\nCredenciales de acceso:')
        self.stdout.write('- Admin: Edward_Fonseca / davit12345')
        self.stdout.write('- Clientes: constructora_alfa, ferreteria_central, obra_norte / davit12345')
        self.stdout.write('- Conductores: carlos_chofer, pedro_trans, luis_driver / davit12345')

