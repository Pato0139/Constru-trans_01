"""Respaldo automático una vez al día, sin dependencias externas.

El proyecto no usa cron ni librerías de planificación, así que se lanza un
hilo daemon desde ``UsuariosConfig.ready()``. El hilo revisa cada cierto
tiempo si ya se generó el respaldo del día (según ``TIME_ZONE``); si no,
ejecuta ``backup_db`` y escribe una marca con la fecha para no repetirlo.
"""

import logging
import os
import sys
import threading
import time
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

logger = logging.getLogger(__name__)

# Comandos de gestión que no deben disparar el planificador.
_COMANDOS_SIN_SCHEDULER = {
    "migrate",
    "makemigrations",
    "test",
    "shell",
    "dumpdata",
    "loaddata",
    "backup_db",
    "collectstatic",
    "createsuperuser",
    "check",
    "flush",
    "showmigrations",
    "sqlmigrate",
    "dbshell",
    "inspectdb",
    "poblar_todo",
    "seed_data",
    "cargar_tipos_material",
    "llenar_datos_prueba",
}

_iniciado = False
_lock = threading.Lock()


def _carpeta_backups():
    destino = Path(getattr(settings, "BASE_DIR", Path.cwd())) / "backups"
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _ruta_marca():
    return _carpeta_backups() / ".ultimo_backup"


def ejecutar_si_corresponde():
    """Genera el respaldo del día si aún no se ha hecho. Devuelve True si lo hizo."""
    hoy = timezone.localdate().isoformat()
    marca = _ruta_marca()
    if marca.exists() and marca.read_text(encoding="utf-8").strip() == hoy:
        return False

    call_command("backup_db", destino="backups", format="both")
    marca.write_text(hoy, encoding="utf-8")
    logger.info("Respaldo diario generado (%s).", hoy)
    return True


def _debe_arrancar():
    """Evita arrancar en comandos de gestión y en el proceso 'watcher' de runserver."""
    argv = sys.argv
    if len(argv) >= 2:
        comando = argv[1]
        if comando in _COMANDOS_SIN_SCHEDULER:
            return False
        if comando == "runserver" and os.environ.get("RUN_MAIN") != "true":
            return False
    return True


def _bucle():
    hora = getattr(settings, "BACKUP_DIARIO_HORA", 2)
    intervalo = getattr(settings, "BACKUP_DIARIO_INTERVALO", 1800)
    while True:
        try:
            if timezone.localtime().hour >= hora:
                ejecutar_si_corresponde()
        except Exception:  # noqa: BLE001 - el hilo no debe morir por un fallo puntual
            logger.exception("Error al ejecutar el respaldo diario.")
        time.sleep(intervalo)


def iniciar_scheduler():
    """Arranca el hilo del respaldo diario una única vez por proceso."""
    global _iniciado
    with _lock:
        if _iniciado or not _debe_arrancar():
            return
        _iniciado = True

    hilo = threading.Thread(target=_bucle, name="backup-diario", daemon=True)
    hilo.start()
    logger.info("Planificador de respaldo diario iniciado.")
