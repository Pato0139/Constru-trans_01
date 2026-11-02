import threading
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.management import call_command
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Evitar múltiples backups simultáneos
backup_lock = threading.Lock()

def run_backup():
    if backup_lock.acquire(blocking=False):
        try:
            logger.info("Iniciando backup automático por modificación en BD...")
            call_command("backup_db", destino="backups", format="sql")
            logger.info("Backup automático completado.")
        except Exception as e:
            logger.error(f"Error en backup automático: {e}")
        finally:
            backup_lock.release()

@receiver(post_save)
@receiver(post_delete)
def trigger_backup_on_change(sender, **kwargs):
    # Excluir modelos de logs o sesiones para evitar bucles infinitos si el backup registra algo
    excluded_models = [
        'Session', 'LogEntry', 'SecurityEvent', 'ActivityLog', 'AuditLog', 'Notification'
    ]
    if sender.__name__ in excluded_models:
        return

    # Ejecutar en un hilo separado para no bloquear la respuesta del usuario
    thread = threading.Thread(target=run_backup)
    thread.start()
