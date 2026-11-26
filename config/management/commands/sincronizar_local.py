"""
Comando de gestión: python manage.py sincronizar_local

Aplica migraciones en SQLite ('local') y descarga todos los registros desde
Neon ('remota') hacia 'local' respetando el orden de llaves foráneas.
"""

from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command

from config.sync_local import sincronizar_remota_a_local
from config.utils import conexion_remota_disponible


class Command(BaseCommand):
    help = "Clona y sincroniza todos los datos desde la base remota (Neon) hacia SQLite local."

    def handle(self, *args, **options):
        if "remota" not in settings.DATABASES:
            raise CommandError("La base remota no está configurada (revisa DATABASE_URL en .env).")
        if not conexion_remota_disponible():
            raise CommandError("No hay conexión disponible con la base remota (Neon).")

        self.stdout.write("Aplicando migraciones en la base local (SQLite)...")
        call_command("migrate", database="local", interactive=False, verbosity=0)

        self.stdout.write("Descargando datos desde Neon ('remota') hacia SQLite ('local')...")
        resumen = sincronizar_remota_a_local()

        total_ok = 0
        total_err = 0
        for item in resumen:
            if item["remotos"] == 0 and item["errores"] == 0:
                continue
            total_ok += item["sincronizados"]
            total_err += item["errores"]
            estado = (
                self.style.SUCCESS(f"{item['sincronizados']}/{item['remotos']}")
                if item["errores"] == 0
                else self.style.WARNING(
                    f"{item['sincronizados']}/{item['remotos']} ({item['errores']} errores)"
                )
            )
            self.stdout.write(f"  - {item['modelo']:35} -> {estado}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSincronización completada: {total_ok} registros sincronizados en local "
                f"({total_err} errores)."
            )
        )
