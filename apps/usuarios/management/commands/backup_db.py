import os
import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.db import connections
from django.utils import timezone


class Command(BaseCommand):
    help = "Genera backup SQL (pg_dump), JSON y copia física de SQLite si aplica."

    def add_arguments(self, parser):
        parser.add_argument(
            "--destino",
            type=str,
            default="backups",
            help="Carpeta donde se guardarán los backups",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["sql", "json", "both"],
            default="both",
            help="Formato del backup: sql, json o both",
        )

    def handle(self, *args, **options):
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
        destino = base_dir / options["destino"]
        destino.mkdir(parents=True, exist_ok=True)

        aliases = list(settings.DATABASES.keys())
        fmt = options["format"]

        for alias in aliases:
            db_config = settings.DATABASES[alias]
            engine = db_config.get("ENGINE", "")
            
            # --- BACKUP SQL (pg_dump) ---
            if fmt in ["sql", "both"] and "postgresql" in engine:
                sql_path = destino / f"{alias}_{timestamp}.sql"
                
                # Intentar obtener DATABASE_URL del entorno o construirla
                db_url = os.environ.get("DATABASE_URL")
                if not db_url and alias == "default":
                    # Si no hay URL, intentamos construirla desde los parámetros
                    user = db_config.get("USER")
                    password = db_config.get("PASSWORD")
                    host = db_config.get("HOST")
                    port = db_config.get("PORT")
                    name = db_config.get("NAME")
                    db_url = f"postgresql://{user}:{password}@{host}:{port}/{name}"

                if db_url:
                    try:
                        self.stdout.write(f"⏳ Generando backup SQL para {alias}...")
                        with open(sql_path, "w") as f:
                            subprocess.run(["pg_dump", db_url], stdout=f, check=True)
                        self.stdout.write(self.style.SUCCESS(f"✅ Backup SQL creado: {sql_path}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"❌ Error en pg_dump: {e}"))

            # --- BACKUP JSON (dumpdata) ---
            if fmt in ["json", "both"]:
                json_path = destino / f"{alias}_{timestamp}.json"
                try:
                    self.stdout.write(f"⏳ Generando backup JSON para {alias}...")
                    with open(json_path, "w", encoding="utf-8") as f:
                        call_command(
                            "dumpdata",
                            database=alias,
                            indent=2,
                            natural_foreign=True,
                            natural_primary=True,
                            exclude=[
                                "contenttypes",
                                "auth.permission",
                                "admin.logentry",
                                "sessions.session",
                            ],
                            stdout=f,
                        )
                    self.stdout.write(self.style.SUCCESS(f"✅ Backup JSON creado: {json_path}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"❌ Error en dumpdata: {e}"))

            # --- COPIA SQLITE ---
            if "sqlite3" in engine:
                name = db_config.get("NAME", "")
                if name:
                    sqlite_file = Path(name)
                    if sqlite_file.exists():
                        copia_sqlite = destino / f"{alias}_{timestamp}.sqlite3"
                        shutil.copy2(sqlite_file, copia_sqlite)
                        self.stdout.write(self.style.SUCCESS(f"✅ Copia SQLite creada: {copia_sqlite}"))

        self.stdout.write(self.style.SUCCESS("🎉 Proceso de backup terminado."))
