import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import connections
from django.utils import timezone


class Command(BaseCommand):
    help = "Genera backup JSON y copia física de SQLite si aplica."

    def add_arguments(self, parser):
        parser.add_argument(
            "--destino",
            type=str,
            default="backups",
            help="Carpeta donde se guardarán los backups",
        )

    def handle(self, *args, **options):
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        destino = base_dir / options["destino"]
        destino.mkdir(parents=True, exist_ok=True)

        aliases = list(settings.DATABASES.keys())

        for alias in aliases:
            json_path = destino / f"{alias}_{timestamp}.json"

            with open(json_path, "w", encoding="utf-8") as f:
                call_command(
                    "dumpdata",
                    database=alias,
                    indent=2,
                    natural_foreign=True,
                    natural_primary=True,
                    exclude=["contenttypes", "auth.permission", "admin.logentry", "sessions.session"],
                    stdout=f,
                )

            self.stdout.write(self.style.SUCCESS(f"✅ Backup JSON creado: {json_path}"))

            engine = connections[alias].settings_dict.get("ENGINE", "")
            name = connections[alias].settings_dict.get("NAME", "")

            if "sqlite3" in engine and name:
                sqlite_file = Path(name)
                if sqlite_file.exists():
                    copia_sqlite = destino / f"{alias}_{timestamp}.sqlite3"
                    shutil.copy2(sqlite_file, copia_sqlite)
                    self.stdout.write(self.style.SUCCESS(f"✅ Copia SQLite creada: {copia_sqlite}"))

        self.stdout.write(self.style.SUCCESS("🎉 Backup terminado."))
