import time
from django.core.management.base import BaseCommand
from django.db import OperationalError, connections
from apps.usuarios.models import Material, Proveedor, Vehiculo, Usuario
from apps.clientes.models import Cliente
from django.contrib.auth.models import User, Group
from apps.inventario.models import MovimientoInventario
from apps.compras.models import Compra, DetalleCompra
from apps.ordenes.models import Orden, Entrega
from apps.facturacion.models import Factura
from apps.pagos.models import Pago
from apps.historial.models import Historial
from django.contrib.admin.models import LogEntry

class Command(BaseCommand):
    help = 'Sincroniza los datos locales pendientes con la base de datos remota (Neon)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--once',
            action='store_true',
            help='Ejecuta la sincronización una sola vez y termina',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sincroniza todos los registros, ignorando el estado de sincronización actual',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando Sincronizador (El Celador) ---'))
        
        force = options.get('force', False)
        if force:
            self.stdout.write(self.style.WARNING('MODO FORZADO: Se sincronizarán todos los registros.'))

        while True:
            try:
                # 1. Verificar si hay conexión con la base remota
                connections['remota'].ensure_connection()
                self.stdout.write(self.style.SUCCESS('Conexión con la nube establecida.'))
                
                # 2. Sincronizar modelos en orden de dependencia
                self.descargar_usuarios() # Traer usuarios nuevos de la nube
                self.sincronizar_grupos(force=force) # auth_group y auth_user_groups
                self.sincronizar_usuarios(force=force) # auth_user, usuario, cliente
                self.sincronizar_modelo(Proveedor, force=force)
                self.sincronizar_modelo(Material, force=force)
                self.sincronizar_modelo(Vehiculo, force=force)
                self.sincronizar_modelo(Compra, force=force) # Sincroniza Compra y DetalleCompra
                self.sincronizar_modelo(Orden, force=force) # Sincroniza Orden y DetalleOrden
                self.sincronizar_modelo(Entrega, force=force)
                self.sincronizar_modelo(Factura, force=force)
                self.sincronizar_modelo(Pago, force=force)
                self.sincronizar_modelo(MovimientoInventario, force=force)
                self.sincronizar_modelo(Historial, force=force)
                self.sincronizar_log_admin() # django_admin_log
                
                # 3. Corregir secuencias en PostgreSQL (IMPORTANTE para evitar errores de ID duplicado)
                self.corregir_secuencias_remotas()
                
            except OperationalError:
                self.stdout.write(self.style.WARNING('Sin conexión con la nube. Reintentando en 30 segundos...'))
            
            if options['once']:
                self.stdout.write(self.style.SUCCESS('Sincronización única completada.'))
                break

            # Esperar antes de la siguiente revisión
            time.sleep(30)

    def sincronizar_grupos(self, force=False):
        """Sincroniza grupos de Django (Group) y las relaciones con usuarios (auth_user_groups)."""
        try:
            self.stdout.write('Sincronizando Grupos y Permisos...')
            # 1. Sincronizar Grupos
            grupos = Group.objects.using('default').all()
            for group in grupos:
                Group.objects.using('remota').update_or_create(
                    id=group.id,
                    defaults={'name': group.name}
                )
            
            # 2. Sincronizar relaciones de usuarios con grupos (auth_user_groups)
            # Como Django no expone auth_user_groups como un modelo directo fácilmente,
            # usamos el manager de la relación through
            users = User.objects.using('default').all()
            for user in users:
                user_remoto = User.objects.using('remota').filter(id=user.id).first()
                if user_remoto:
                    # Obtenemos los IDs de los grupos locales
                    grupos_ids = list(user.groups.values_list('id', flat=True))
                    # Limpiamos y asignamos en la remota
                    user_remoto.groups.set(Group.objects.using('remota').filter(id__in=grupos_ids))
            
            self.stdout.write(self.style.SUCCESS('  [OK] Grupos y relaciones sincronizados.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] Falló sincronización de Grupos: {str(e)}'))

    def sincronizar_modelo(self, modelo, force=False):
        """Busca registros no sincronizados localmente y los sube a la nube en orden."""
        # Ordenamos por ID para asegurar que se sincronicen en el orden en que fueron creados
        if force:
            pendientes = modelo.objects.using('default').all().order_by('id')
        else:
            pendientes = modelo.objects.using('default').filter(sincronizado=False).order_by('id')
        
        if pendientes.exists():
            self.stdout.write(f'Sincronizando {pendientes.count()} registros de {modelo.__name__}...')
            for obj in pendientes:
                try:
                    # 1. Guardamos el objeto principal en la remota
                    # Usamos update_or_create para evitar duplicados por ID
                    data = {}
                    for field in obj._meta.fields:
                        if field.name != 'sincronizado':
                            # Manejar campos ForeignKey para asegurar que el ID se pase correctamente
                            if field.is_relation and field.many_to_one:
                                data[field.name + '_id'] = getattr(obj, field.name + '_id')
                            else:
                                data[field.name] = getattr(obj, field.name)
                    
                    # Forzar el ID para mantener consistencia
                    modelo.objects.using('remota').update_or_create(
                        id=obj.id,
                        defaults=data
                    )
                    
                    # 2. Si tiene detalles (Compra/Orden), los sincronizamos también
                    for rel in obj._meta.related_objects:
                        if rel.get_accessor_name() == 'detalles':
                            detalles = getattr(obj, 'detalles').all().order_by('id')
                            for detalle in detalles:
                                d_data = {}
                                for d_field in detalle._meta.fields:
                                    if d_field.is_relation and d_field.many_to_one:
                                        d_data[d_field.name + '_id'] = getattr(detalle, d_field.name + '_id')
                                    else:
                                        d_data[d_field.name] = getattr(detalle, d_field.name)
                                
                                detalle.__class__.objects.using('remota').update_or_create(
                                    id=detalle.id,
                                    defaults=d_data
                                )
                    
                    # 3. Marcamos como sincronizado localmente
                    obj.sincronizado = True
                    obj.save(using='default')
                    self.stdout.write(self.style.SUCCESS(f'  [OK] {obj} y sus detalles sincronizados.'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] Falló sincronización de {obj}: {str(e)}'))

    def sincronizar_log_admin(self):
        """Sincroniza los logs del administrador de Django."""
        try:
            # Obtenemos el último ID sincronizado en la remota
            ultimo_id_remoto = LogEntry.objects.using('remota').order_by('-id').first()
            ultimo_id = ultimo_id_remoto.id if ultimo_id_remoto else 0
            
            pendientes = LogEntry.objects.using('default').filter(id__gt=ultimo_id).order_by('id')
            
            if pendientes.exists():
                self.stdout.write(f'Sincronizando {pendientes.count()} logs de Django Admin...')
                for log in pendientes:
                    data = {}
                    for field in log._meta.fields:
                        if field.is_relation and field.many_to_one:
                            data[field.name + '_id'] = getattr(log, field.name + '_id')
                        else:
                            data[field.name] = getattr(log, field.name)
                    
                    LogEntry.objects.using('remota').update_or_create(
                        id=log.id,
                        defaults=data
                    )
                self.stdout.write(self.style.SUCCESS(f'  [OK] {pendientes.count()} logs sincronizados.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] Falló sincronización de LogEntry: {str(e)}'))

    def sincronizar_usuarios(self, force=False):
        """Sincroniza usuarios de Django (User), perfiles extendidos (Usuario) y perfiles específicos (Cliente)."""
        if force:
            usuarios_pendientes = Usuario.objects.using('default').all().order_by('id')
        else:
            usuarios_pendientes = Usuario.objects.using('default').filter(sincronizado=False).order_by('id')
            self.stdout.write(f'Sincronizando {usuarios_pendientes.count()} usuarios...')
            for perfil in usuarios_pendientes:
                try:
                    # 1. Sincronizar el User de Django primero
                    user_django = perfil.user
                    u_data = {}
                    for field in user_django._meta.fields:
                        u_data[field.name] = getattr(user_django, field.name)
                    
                    User.objects.using('remota').update_or_create(
                        id=user_django.id,
                        defaults=u_data
                    )
                    
                    # 2. Sincronizar el perfil Usuario
                    p_data = {}
                    for field in perfil._meta.fields:
                        if field.name != 'sincronizado':
                            p_data[field.name] = getattr(perfil, field.name)
                    
                    Usuario.objects.using('remota').update_or_create(
                        id=perfil.id,
                        defaults=p_data
                    )
                    
                    # 3. Sincronizar perfiles específicos si existen
                    if perfil.rol == 'cliente':
                        try:
                            cliente_perfil = Cliente.objects.using('default').get(usuario=perfil)
                            c_data = {}
                            for field in cliente_perfil._meta.fields:
                                c_data[field.name] = getattr(cliente_perfil, field.name)
                            
                            Cliente.objects.using('remota').update_or_create(
                                id=cliente_perfil.id,
                                defaults=c_data
                            )
                            self.stdout.write(self.style.SUCCESS(f'    [OK] Perfil de Cliente sincronizado para {perfil.user.username}'))
                        except Cliente.DoesNotExist:
                            pass
                    
                    # 4. Marcar como sincronizado local
                    perfil.sincronizado = True
                    perfil.save(using='default')
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Usuario {perfil.user.username} y sus perfiles sincronizados.'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] Falló sincronización de usuario {perfil}: {e}'))

    def descargar_usuarios(self):
        """Descarga datos base (Usuarios, Materiales, Vehículos, Proveedores) desde la nube."""
        try:
            self.stdout.write('Descargando datos base desde la nube...')
            
            # 1. Usuarios
            usuarios_remotos = User.objects.using('remota').all()
            for u_remoto in usuarios_remotos:
                User.objects.using('default').update_or_create(
                    id=u_remoto.id,
                    defaults={
                        'username': u_remoto.username,
                        'password': u_remoto.password,
                        'email': u_remoto.email,
                        'first_name': u_remoto.first_name,
                        'last_name': u_remoto.last_name,
                        'is_staff': u_remoto.is_staff,
                        'is_active': u_remoto.is_active,
                        'is_superuser': u_remoto.is_superuser,
                        'last_login': u_remoto.last_login,
                        'date_joined': u_remoto.date_joined,
                    }
                )
                p_remoto = Usuario.objects.using('remota').filter(user_id=u_remoto.id).first()
                if p_remoto:
                    Usuario.objects.using('default').update_or_create(
                        id=p_remoto.id,
                        defaults={'user_id': u_remoto.id, 'rol': p_remoto.rol, 'telefono': p_remoto.telefono, 'direccion': p_remoto.direccion, 'sincronizado': True}
                    )

            # 2. Proveedores
            for p in Proveedor.objects.using('remota').all():
                Proveedor.objects.using('default').update_or_create(
                    id=p.id, defaults={'nombre': p.nombre, 'nit': p.nit, 'telefono': p.telefono, 'correo': p.correo, 'direccion': p.direccion, 'sincronizado': True}
                )

            # 3. Materiales
            for m in Material.objects.using('remota').all():
                Material.objects.using('default').update_or_create(
                    id=m.id, defaults={'nombre': m.nombre, 'descripcion': m.descripcion, 'precio_unitario': m.precio_unitario, 'stock_actual': m.stock_actual, 'stock_minimo': m.stock_minimo, 'unidad_medida': m.unidad_medida, 'sincronizado': True}
                )

            # 4. Vehículos
            for v in Vehiculo.objects.using('remota').all():
                Vehiculo.objects.using('default').update_or_create(
                    id=v.id, defaults={'placa': v.placa, 'modelo': v.modelo, 'capacidad_carga': v.capacidad_carga, 'estado': v.estado, 'sincronizado': True}
                )

            self.stdout.write(self.style.SUCCESS('  [OK] Usuarios actualizados desde la nube.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] Falló la descarga de datos: {str(e)}'))

    def corregir_secuencias_remotas(self):
        """Reinicia las secuencias de PostgreSQL para que coincidan con el máximo ID actual."""
        try:
            self.stdout.write('Corrigiendo secuencias en la nube...')
            with connections['remota'].cursor() as cursor:
                # Lista de tablas y sus secuencias comunes en Django
                tablas = [
                    ('auth_user', 'id'),
                    ('usuario', 'id'),
                    ('material', 'id'),
                    ('vehiculo', 'id'),
                    ('proveedor', 'id'),
                    ('orden', 'id'),
                    ('factura', 'id'),
                    ('historial_actividad', 'id'),
                    ('perfil_cliente', 'id'),
                ]
                for tabla, columna in tablas:
                    try:
                        # SQL robusto para PostgreSQL que detecta el nombre de la secuencia automáticamente
                        sql = f"SELECT setval(pg_get_serial_sequence('{tabla}', '{columna}'), (SELECT MAX({columna}) FROM {tabla}));"
                        cursor.execute(sql)
                    except Exception:
                        continue # Si una tabla no existe o no tiene secuencia, seguimos
            self.stdout.write(self.style.SUCCESS('  [OK] Secuencias de la nube corregidas.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  [ERROR] Falló corregir secuencias: {str(e)}'))
