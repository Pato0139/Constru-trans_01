from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from .models import Usuario, Material, Stock, Notificacion
import threading
import os

from django.core.cache import cache

@receiver(post_save, sender=Notificacion)
def invalidate_notif_cache(sender, instance, **kwargs):
    """Invalida el caché de notificaciones cuando llega una nueva"""
    if instance.usuario:
        cache.delete(f'notif_user_{instance.usuario.user.id}')

@receiver(post_save, sender=Material)
def create_material_stock(sender, instance, created, **kwargs):
    """Crea un registro de Stock cuando se crea un nuevo Material"""
    if created:
        Stock.objects.get_or_create(material=instance)

# -------------------------
# RESPALDO AUTOMÁTICO A JSON (Para el Repositorio)
# -------------------------
# Global variable to track the last backup time to avoid saturation
LAST_BACKUP_TIME = 0
BACKUP_COOLDOWN = 300  # 5 minutes in seconds

def realizar_backup_async():
    """Ejecuta dumpdata y sube los cambios al repositorio en un hilo separado"""
    global LAST_BACKUP_TIME
    import time
    
    current_time = time.time()
    if current_time - LAST_BACKUP_TIME < BACKUP_COOLDOWN:
        # Skip if a backup was performed recently
        return

    LAST_BACKUP_TIME = current_time
    try:
        from django.conf import settings
        import subprocess
        
        # 1. Crear el respaldo en JSON
        backup_path = os.path.join(settings.BASE_DIR, 'db_backup.json')
        with open(backup_path, 'w', encoding='utf-8') as f:
            call_command('dumpdata', indent=2, stdout=f, exclude=['contenttypes', 'auth.Permission'])
        
        # 2. Intentar subir al repositorio (git)
        # Solo si estamos en un repositorio git
        try:
            # Añadir la base de datos sqlite y el respaldo json
            subprocess.run(['git', 'add', 'db.sqlite3', 'db_backup.json'], cwd=settings.BASE_DIR, capture_output=True)
            
            # Commit con mensaje automático
            commit_res = subprocess.run(['git', 'commit', '-m', 'Auto-backup: Base de datos actualizada'], cwd=settings.BASE_DIR, capture_output=True)
            
            # Si hubo commit (o no había nada nuevo pero queremos intentar push), hacemos push
            if commit_res.returncode == 0:
                subprocess.run(['git', 'push'], cwd=settings.BASE_DIR, capture_output=True)
                
        except Exception as git_e:
            print(f"Error en git auto-backup: {git_e}")

    except Exception as e:
        print(f"Error en backup automático: {e}")

@receiver(post_save, sender=Usuario)
@receiver(post_save, sender=Material)
@receiver(post_save, sender=User)
@receiver(post_save, sender='ordenes.Orden')
@receiver(post_save, sender='clientes.Cliente')
@receiver(post_save, sender='compras.Compra')
@receiver(post_save, sender='pagos.Pago')
@receiver(post_save, sender='historial.Historial')
def trigger_backup_and_sync(sender, instance, **kwargs):
    """Dispara el respaldo y la sincronización cada vez que hay cambios importantes"""
    # 1. Respaldo en JSON/Git
    if not os.getenv('SKIP_AUTO_BACKUP') == 'True':
        import time
        current_time = time.time()
        if current_time - LAST_BACKUP_TIME >= BACKUP_COOLDOWN:
            thread = threading.Thread(target=realizar_backup_async)
            thread.start()
    
    # 2. Sincronización con Neon (Nube)
    # Ejecutamos 'sincronizar --once' en un hilo para no bloquear la respuesta al usuario
    def run_sync():
        try:
            call_command('sincronizar', once=True)
        except Exception as e:
            print(f"Error en sincronización automática: {e}")

    sync_thread = threading.Thread(target=run_sync)
    sync_thread.start()

# -------------------------
# PROTECCIÓN DE SUPERUSUARIO GLOBAL
# -------------------------
PROTECTED_USERNAME = 'Edward_Fonseca'

@receiver(pre_save, sender=User)
def protect_global_admin_update(sender, instance, **kwargs):
    """Evita que se le quite el estado de superusuario al administrador global"""
    if instance.username == PROTECTED_USERNAME:
        # Forzar que siempre sea superusuario y staff
        instance.is_superuser = True
        instance.is_staff = True
        instance.is_active = True

@receiver(pre_save, sender=Usuario)
def protect_usuario_rol_update(sender, instance, **kwargs):
    """Evita que se le quite el rol de admin al administrador global en su perfil"""
    if instance.user and instance.user.username == PROTECTED_USERNAME:
        instance.rol = 'admin'
        instance.estado = 'activo'

@receiver(pre_delete, sender=User)
def protect_global_admin_delete(sender, instance, **kwargs):
    """Evita que el administrador global sea eliminado"""
    if instance.username == PROTECTED_USERNAME:
        raise PermissionDenied("No se puede eliminar al Administrador Global del sistema.")

@receiver(pre_delete, sender=Usuario)
def protect_usuario_perfil_delete(sender, instance, **kwargs):
    """Evita que el perfil de Usuario del administrador global sea eliminado"""
    if instance.user and instance.user.username == PROTECTED_USERNAME:
        raise PermissionDenied("No se puede eliminar el perfil del Administrador Global.")
