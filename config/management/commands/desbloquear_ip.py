"""
Comando para desbloquear direcciones IP bloqueadas por seguridad.

Uso:
    python manage.py desbloquear_ip 127.0.0.1
    python manage.py desbloquear_ip --localhost
    python manage.py desbloquear_ip --todas
"""

from django.core.management.base import BaseCommand
from config.models import BloqueoIP
from config.security import desbloquear_ip, LOOPBACK_IPS


class Command(BaseCommand):
    help = "Desbloquea direcciones IP y limpia la caché de seguridad."

    def add_arguments(self, parser):
        parser.add_argument("ip", nargs="?", type=str, help="Dirección IP a desbloquear")
        parser.add_argument(
            "--localhost",
            action="store_true",
            help="Desbloquea todas las IPs locales de loopback (127.0.0.1, ::1, etc.)",
        )
        parser.add_argument(
            "--todas",
            action="store_true",
            help="Desbloquea todas las IPs actualmente bloqueadas",
        )

    def handle(self, *args, **options):
        ip = options.get("ip")
        es_localhost = options.get("localhost")
        todas = options.get("todas")

        if not ip and not es_localhost and not todas:
            # Por defecto si no se pasa argumento, desbloquear localhost
            es_localhost = True

        if todas:
            bloqueos = list(BloqueoIP.objects.filter(activo=True).values_list("ip", flat=True))
            if not bloqueos:
                self.stdout.write(self.style.SUCCESS("No hay IPs bloqueadas actualmente."))
                return
            for bloq_ip in set(bloqueos):
                desbloquear_ip(bloq_ip)
                self.stdout.write(self.style.SUCCESS(f"IP {bloq_ip} desbloqueada correctamente."))
            return

        if es_localhost:
            for loopback in LOOPBACK_IPS:
                desbloquear_ip(loopback)
                self.stdout.write(self.style.SUCCESS(f"IP local {loopback} desbloqueada."))
            return

        if ip:
            desbloquear_ip(ip)
            self.stdout.write(self.style.SUCCESS(f"IP {ip} desbloqueada correctamente."))
