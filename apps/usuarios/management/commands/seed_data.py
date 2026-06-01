# Comando seed: AUTH_USER_MODEL = usuarios.Usuario (NO usar django.contrib.auth.models.User)

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models.signals import post_save
from django.utils import timezone

from apps.clientes.models import Cliente, crear_perfil_cliente
from core.routers import EnrutadorInventario
from core.utils import conexion_remota_disponible
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

DEFAULT_PASSWORD = 'davit12345'
_router = EnrutadorInventario()


class Command(BaseCommand):
    help = 'Llena la base de datos con datos de prueba'

    def _db_for(self, model):
        """Usa la misma BD que el router híbrido (remota si hay Neon, si no local)."""
        return _router.db_for_write(model, **{}) or 'default'

    def _databases_to_seed(self):
        """Pobla remota (Neon) si hay conexión; siempre incluye SQLite local."""
        if 'remota' in settings.DATABASES and conexion_remota_disponible():
            return ['remota', 'default']
        return ['default']

    def _ensure_usuario(self, db_alias, username, email, rol, nombres, apellidos, documento, **extra):
        """Crea o recupera un Usuario (AUTH_USER_MODEL = usuarios.Usuario)."""
        usuario, created = Usuario.objects.using(db_alias).get_or_create(
            username=username,
            defaults={
                'email': email,
                'nombres': nombres,
                'apellidos': apellidos,
                'documento': documento,
                'tipo_documento': 'CC',
                'rol': rol,
                'estado': 'activo',
                **extra,
            },
        )
        if created:
            usuario.set_password(DEFAULT_PASSWORD)
            usuario.save(using=db_alias)
        return usuario, created

    def _get_or_create_material(self, db_alias, m_data):
        """Evita MultipleObjectsReturned si hay duplicados por nombre."""
        qs = MaterialConstruccion.objects.using(db_alias).filter(nombre=m_data['nombre'])
        mat = qs.first()
        if mat:
            return mat, False
        mat = MaterialConstruccion.objects.using(db_alias).create(**m_data)
        return mat, True

    def add_arguments(self, parser):
        parser.add_argument(
            '--force-pedidos',
            action='store_true',
            help='Crea pedidos de demo aunque el cliente ya tenga pedidos',
        )

    def _seed_database(self, db_alias, force_pedidos=False):
        self.stdout.write(self.style.NOTICE(f'\n--- Poblando base de datos: {db_alias} ---'))

        # 0. Superusuario / administrador
        admin_user, created = self._ensure_usuario(
            db_alias,
            username='Edward_Fonseca',
            email='edwardf5432@gmail.com',
            rol='admin',
            nombres='Edward',
            apellidos='Fonseca',
            documento='10101010',
            is_staff=True,
            is_superuser=True,
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Administrador Edward_Fonseca creado.'))
        else:
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.save(using=db_alias)

        # 1. EPS (requerida para conductores)
        eps, _ = EPS.objects.using(db_alias).get_or_create(
            codigo_eps='EPS001',
            defaults={
                'numero_seguro': '123456789',
                'ciudad': 'Bogota',
                'direccion': 'Calle 100 # 10-10',
                'telefono': '3101234567',
                'correo': 'contacto@eps.com',
            },
        )

        # 2. Proveedores
        proveedores_data = [
            {
                'nombre_empresa': 'Aceros de Colombia S.A.',
                'nit': '900123456',
                'telefono': '3105556677',
                'correo': 'ventas@aceroscol.com',
                'descripcion': 'Proveedor de materiales de acero',
            },
            {
                'nombre_empresa': 'Cales y Arenas del Sur',
                'nit': '800987654',
                'telefono': '3208889900',
                'correo': 'contacto@calessur.com',
                'descripcion': 'Proveedor de arenas y gravas',
            },
        ]

        for p_data in proveedores_data:
            prov, created = Proveedor.objects.using(db_alias).get_or_create(
                nit=p_data['nit'],
                defaults=p_data,
            )
            if created:
                self.stdout.write(f'Proveedor creado: {prov.nombre_empresa}')

        # 3. Materiales y stock
        materiales_data = [
            {'nombre': 'Cemento Gris Argos 50kg', 'unidad_medida': 'Bulto', 'precio_referencia': 28500, 'descripcion': 'Bulto de cemento gris para construccion general'},
            {'nombre': 'Varilla Corrugada 1/2"', 'unidad_medida': 'Unidad', 'precio_referencia': 35000, 'descripcion': 'Varilla de acero estructural 6 metros'},
            {'nombre': 'Arena de Rio (m3)', 'unidad_medida': 'm3', 'precio_referencia': 85000, 'descripcion': 'Arena fina para acabados'},
            {'nombre': 'Grava 3/4 (m3)', 'unidad_medida': 'm3', 'precio_referencia': 92000, 'descripcion': 'Grava triturada para concreto'},
            {'nombre': 'Ladrillo Estructural', 'unidad_medida': 'Unidad', 'precio_referencia': 1200, 'descripcion': 'Ladrillo de arcilla cocida'},
        ]

        mats = []
        for m_data in materiales_data:
            mat, created = self._get_or_create_material(db_alias, m_data)
            mats.append(mat)

            stock, s_created = Stock.objects.using(db_alias).get_or_create(
                material=mat,
                defaults={'cantidad_actual': 1000, 'stock_minimo': 100, 'ubicacion': 'Bodega Principal'},
            )
            if not s_created:
                stock.cantidad_actual = 1000
                stock.save(using=db_alias)
            self.stdout.write(f'Material: {mat.nombre} - Stock: {stock.cantidad_actual}')

        # 4. Conductores y vehículos
        conductores_data = [
            {'username': 'carlos_chofer', 'email': 'carlos@constru.com', 'nombres': 'Carlos', 'apellidos': 'Mendoza', 'doc': '778899', 'placa': 'TRX-101', 'marca': 'Toyota', 'modelo': 'Hilux', 'tipo': 'Camion 5 Ton', 'capacidad': 5.0},
            {'username': 'pedro_trans', 'email': 'pedro@constru.com', 'nombres': 'Pedro', 'apellidos': 'Salas', 'doc': '554433', 'placa': 'KLM-202', 'marca': 'Chevrolet', 'modelo': 'Silverado', 'tipo': 'Bolqueta 10 Ton', 'capacidad': 10.0},
            {'username': 'luis_driver', 'email': 'luis@constru.com', 'nombres': 'Luis', 'apellidos': 'Garcia', 'doc': '998877', 'placa': 'ABC-123', 'marca': 'Ford', 'modelo': 'F-150', 'tipo': 'Camion 3 Ton', 'capacidad': 3.0},
        ]

        conductores_usuarios = []
        vehiculos_creados = []
        for c_data in conductores_data:
            p_cond, created = self._ensure_usuario(
                db_alias,
                username=c_data['username'],
                email=c_data['email'],
                rol='conductor',
                nombres=c_data['nombres'],
                apellidos=c_data['apellidos'],
                documento=c_data['doc'],
            )
            if created:
                self.stdout.write(f'Conductor usuario creado: {p_cond.username}')

            cond_profile, _ = Conductor.objects.using(db_alias).get_or_create(
                usuario=p_cond,
                defaults={
                    'numero_licencia': f'LIC-{c_data["doc"]}',
                    'categoria_licencia': 'C2',
                    'fecha_vencimiento_licencia': date.today() + timedelta(days=365),
                    'estado': 'activo',
                    'eps': eps,
                },
            )

            vehiculo, _ = Vehiculo.objects.using(db_alias).get_or_create(
                placa=c_data['placa'],
                defaults={
                    'marca': c_data['marca'],
                    'modelo': c_data['modelo'],
                    'tipo_vehiculo': c_data['tipo'],
                    'capacidad_carga': c_data['capacidad'],
                    'estado': 'disponible',
                },
            )
            vehiculos_creados.append(vehiculo)

            ConductorVehiculo.objects.using(db_alias).get_or_create(
                conductor=cond_profile,
                vehiculo=vehiculo,
            )

            conductores_usuarios.append(p_cond)
            self.stdout.write(f'Conductor {p_cond.nombres} y Vehiculo {c_data["placa"]} listos.')

        # 5. Clientes y pedidos
        clientes_data = [
            {'username': 'constructora_alfa', 'email': 'proyectos@alfa.com', 'nombres': 'Ing. Roberto', 'apellidos': 'Torres', 'doc': '112233', 'empresa': 'Constructora Alfa SAS'},
            {'username': 'ferreteria_central', 'email': 'compras@central.com', 'nombres': 'Lucia', 'apellidos': 'Perez', 'doc': '445566', 'empresa': 'Ferreteria Central'},
            {'username': 'obra_norte', 'email': 'obra@norte.com', 'nombres': 'Andres', 'apellidos': 'Rodriguez', 'doc': '776655', 'empresa': 'Obra Norte Ltda'},
        ]

        for cl_data in clientes_data:
            p_cl, created = self._ensure_usuario(
                db_alias,
                username=cl_data['username'],
                email=cl_data['email'],
                rol='cliente',
                nombres=cl_data['nombres'],
                apellidos=cl_data['apellidos'],
                documento=cl_data['doc'],
            )

            cliente_perfil, _ = Cliente.objects.using(db_alias).get_or_create(
                usuario=p_cl,
                defaults={
                    'nombre_empresa': cl_data['empresa'],
                    'direccion_principal': 'Av Siempre Viva 123',
                    'tipo_cliente': 'empresa',
                },
            )
            cliente_perfil.nombre_empresa = cl_data['empresa']
            cliente_perfil.direccion_principal = 'Av Siempre Viva 123'
            cliente_perfil.tipo_cliente = 'empresa'
            cliente_perfil.save(using=db_alias)

            if not force_pedidos and Pedido.objects.using(db_alias).filter(usuario=p_cl).exists():
                self.stdout.write(
                    f'Cliente {cl_data["empresa"]}: ya tiene pedidos (use --force-pedidos para duplicar).'
                )
                continue

            estados_pedido = ['pendiente', 'en_ruta', 'entregado']
            for idx, estado_p in enumerate(estados_pedido):
                pedido = Pedido.objects.using(db_alias).create(
                    usuario=p_cl,
                    cliente=cliente_perfil,
                    direccion_destino=f'Tunja — Obra {cl_data["empresa"]} - Calle {100 + idx}',
                    estado=estado_p,
                )

                for mat in mats[:3]:
                    cantidad = 20 + (idx * 10)
                    DetallePedido.objects.using(db_alias).create(
                        pedido=pedido,
                        material=mat,
                        cantidad=cantidad,
                        precio_unitario=mat.precio_referencia,
                    )

                pedido.calcular_total(using=db_alias)

                if estado_p != 'pendiente' and conductores_usuarios and vehiculos_creados:
                    conductor_idx = idx % len(conductores_usuarios)
                    entrega = Entrega.objects.using(db_alias).create(
                        pedido=pedido,
                        conductor=conductores_usuarios[conductor_idx],
                        vehiculo=vehiculos_creados[conductor_idx],
                        direccion_entrega=pedido.direccion_destino,
                        estado='pendiente' if estado_p == 'en_ruta' else 'entregado',
                        fecha_salida=timezone.now(),
                    )
                    if estado_p == 'entregado':
                        entrega.fecha_entrega = timezone.now()
                        entrega.save(using=db_alias)

                self.stdout.write(
                    f'Cliente {cl_data["empresa"]} - Pedido #{pedido.codigo_pedido} ({estado_p}) creado.'
                )

        # 6. Movimientos de inventario
        self.stdout.write('\nGenerando movimientos de inventario...')
        for mat in mats:
            MovimientoInventario.objects.using(db_alias).create(
                material=mat,
                tipo_movimiento='entrada',
                cantidad=1000,
                observacion='Carga inicial de inventario - Seeding',
            )
            self.stdout.write(f'Movimiento de entrada creado para: {mat.nombre}')

        self.stdout.write(self.style.SUCCESS('\nDatos de prueba generados exitosamente!'))
        self.stdout.write('\nCredenciales de acceso:')
        self.stdout.write(f'- Admin: Edward_Fonseca / {DEFAULT_PASSWORD}')
        self.stdout.write(f'- Clientes: constructora_alfa, ferreteria_central, obra_norte / {DEFAULT_PASSWORD}')
        self.stdout.write(f'- Conductores: carlos_chofer, pedro_trans, luis_driver / {DEFAULT_PASSWORD}')

    def handle(self, *args, **options):
        force_pedidos = options.get('force_pedidos', False)
        self.stdout.write('Iniciando creacion de datos de prueba completos...')
        # Evitar que el signal cree Cliente en otra BD durante el seed
        post_save.disconnect(crear_perfil_cliente, sender=Usuario)
        try:
            for db_alias in self._databases_to_seed():
                self._seed_database(db_alias, force_pedidos=force_pedidos)
        finally:
            post_save.connect(crear_perfil_cliente, sender=Usuario)

        self.stdout.write(self.style.SUCCESS('\nProceso de seed finalizado en todas las bases configuradas.'))
