import time
from django.core.management.base import BaseCommand
from django.db import OperationalError, connections
from apps.usuarios.models import Material, Proveedor, Vehiculo, Usuario
from django.contrib.auth.models import User
from apps.inventario.models import MovimientoInventario
from apps.compras.models import Compra
from apps.ordenes.models import Orden

class Command(BaseCommand):
    help = 'Sincroniza los datos locales pendientes con la base de datos remota (Neon)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando Sincronizador (El Celador) ---'))
        
        while True:
            try:
                # 1. Verificar si hay conexión con la base remota
                connections['remota'].ensure_connection()
                self.stdout.write(self.style.SUCCESS('Conexión con la nube establecida.'))
                
                # 2. Sincronizar modelos
                self.sincronizar_usuarios()
                self.sincronizar_modelo(Material)
                self.sincronizar_modelo(Proveedor)
                self.sincronizar_modelo(Vehiculo)
                self.sincronizar_modelo(Compra)
                self.sincronizar_modelo(Orden)
                self.sincronizar_modelo(MovimientoInventario)
                
            except OperationalError:
                self.stdout.write(self.style.WARNING('Sin conexión con la nube. Reintentando en 30 segundos...'))
            
            # Esperar antes de la siguiente revisión
            time.sleep(30)

    def sincronizar_modelo(self, modelo):
        """Busca registros no sincronizados localmente y los sube a la nube."""
        pendientes = modelo.objects.using('default').filter(sincronizado=False)
        
        if pendientes.exists():
            self.stdout.write(f'Sincronizando {pendientes.count()} registros de {modelo.__name__}...')
            for obj in pendientes:
                try:
                    # 1. Guardamos el objeto principal en la remota
                    obj.save(using='remota')
                    
                    # 2. Si tiene detalles (Compra/Orden), los sincronizamos también
                    if hasattr(obj, 'detalles'):
                        for detalle in obj.detalles.all():
                            detalle.save(using='remota')
                    
                    # 3. Marcamos como sincronizado localmente
                    obj.sincronizado = True
                    obj.save(using='default')
                    self.stdout.write(self.style.SUCCESS(f'  [OK] {obj} y sus detalles sincronizados.'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] Falló sincronización de {obj}: {e}'))

    def sincronizar_usuarios(self):
        """Sincroniza usuarios de Django (User) y perfiles extendidos (Usuario)."""
        usuarios_pendientes = Usuario.objects.using('default').filter(sincronizado=False)
        
        if usuarios_pendientes.exists():
            self.stdout.write(f'Sincronizando {usuarios_pendientes.count()} usuarios...')
            for perfil in usuarios_pendientes:
                try:
                    # 1. Sincronizar el User de Django primero
                    user_django = perfil.user
                    user_django.save(using='remota')
                    
                    # 2. Sincronizar el perfil Usuario
                    perfil.save(using='remota')
                    
                    # 3. Marcar como sincronizado local
                    perfil.sincronizado = True
                    perfil.save(using='default')
                    self.stdout.write(self.style.SUCCESS(f'  [OK] Usuario {perfil.user.username} sincronizado.'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  [ERROR] Falló sincronización de usuario {perfil}: {e}'))
