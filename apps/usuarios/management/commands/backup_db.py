"""Respaldo de la base de datos desmembrado por aplicación.

En lugar de generar un único volcado gigante de toda la base, se crea un archivo
por cada aplicación de Django (por ejemplo ``pedidos_..._...sql``,
``catalogo_..._.sql``). Así el respaldo es más liviano, se puede revisar/versionar
por separado y permite recuperar solo la aplicación que haga falta.
"""

import os
import shutil
import subprocess
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand, call_command
from django.utils import timezone

# Aplicaciones de sistema cuyo contenido ya se excluye al exportar JSON.
APPS_SIN_JSON = {"contenttypes", "admin", "sessions"}

MODELOS_EXCLUIDOS_JSON = [
    "contenttypes",
    "auth.permission",
    "admin.logentry",
    "sessions.session",
]


def _apps_con_tablas():
    """Devuelve [(app_label, [tablas...]), ...] para las apps con modelos."""
    seleccion = []
    for config in apps.get_app_configs():
        tablas = []
        for modelo in config.get_models():
            meta = modelo._meta
            if meta.proxy or not meta.managed or meta.swapped:
                continue
            if meta.db_table not in tablas:
                tablas.append(meta.db_table)
        if tablas:
            seleccion.append((config.label, tablas))
    return seleccion


def _bases_unicas():
    """Evita respaldar dos veces la misma base (ej. ``default`` y ``local``)."""
    vistas = set()
    bases = []
    for alias, config in settings.DATABASES.items():
        clave = (
            config.get("ENGINE", ""),
            str(config.get("NAME", "")),
            config.get("HOST", ""),
            str(config.get("PORT", "")),
        )
        if clave in vistas:
            continue
        vistas.add(clave)
        bases.append((alias, config))
    return bases


def _url_postgres(db_config):
    """Obtiene la cadena de conexión de PostgreSQL para ``pg_dump``."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    user = db_config.get("USER")
    host = db_config.get("HOST")
    name = db_config.get("NAME")
    if not (user and host and name):
        return None

    password = db_config.get("PASSWORD")
    port = db_config.get("PORT")
    credenciales = f"{user}:{password}@" if password else f"{user}@"
    return f"postgresql://{credenciales}{host}:{port}/{name}"


def _dump_sql_por_app(db_url, etiqueta, timestamp, destino, log):
    """Genera un archivo SQL por aplicación usando ``pg_dump``."""
    creados = []
    for app_label, tablas in _apps_con_tablas():
        archivo = destino / f"{app_label}_{etiqueta}_{timestamp}.sql"
        comando = [
            "pg_dump",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            db_url,
        ]
        comando += [f"--table={tabla}" for tabla in tablas]

        try:
            with open(archivo, "w", encoding="utf-8") as f:
                subprocess.run(comando, stdout=f, stderr=subprocess.PIPE, check=True)
            creados.append(archivo)
        except subprocess.CalledProcessError as error:
            detalle = (error.stderr or b"").decode("utf-8", "ignore").strip()
            log(f"❌ Error en pg_dump ({app_label}): {detalle or error}")
            archivo.unlink(missing_ok=True)
        except FileNotFoundError:
            log("❌ No se encontró 'pg_dump' en el sistema.")
            archivo.unlink(missing_ok=True)
            break
    return creados


def _dump_json_por_app(alias, timestamp, destino, log):
    """Genera un archivo JSON por aplicación usando ``dumpdata``."""
    creados = []
    for app_label, _tablas in _apps_con_tablas():
        if app_label in APPS_SIN_JSON:
            continue

        archivo = destino / f"{app_label}_{alias}_{timestamp}.json"
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                call_command(
                    "dumpdata",
                    app_label,
                    database=alias,
                    indent=2,
                    natural_foreign=True,
                    natural_primary=True,
                    exclude=MODELOS_EXCLUIDOS_JSON,
                    stdout=f,
                )
            creados.append(archivo)
        except Exception as error:  # noqa: BLE001 - se reporta y continúa con el resto
            log(f"❌ Error en dumpdata ({app_label}): {error}")
            archivo.unlink(missing_ok=True)
    return creados


def _copiar_sqlite(etiqueta, db_config, timestamp, destino, log):
    """Copia física del archivo SQLite, si aplica."""
    name = db_config.get("NAME", "")
    if not name:
        return None

    sqlite_file = Path(name)
    if not sqlite_file.exists():
        return None

    copia = destino / f"{etiqueta}_{timestamp}.sqlite3"
    shutil.copy2(sqlite_file, copia)
    log(f"✅ Copia SQLite creada: {copia.name}")
    return copia


def generar_backup(destino="backups", fmt="both", log=print):
    """Genera los respaldos por aplicación y devuelve la lista de archivos creados."""
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    base_dir = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    carpeta = base_dir / destino
    carpeta.mkdir(parents=True, exist_ok=True)

    creados = []

    for alias, db_config in _bases_unicas():
        engine = db_config.get("ENGINE", "")

        if "postgresql" in engine:
            db_url = _url_postgres(db_config)
            if not db_url:
                log(f"⚠️  Sin cadena de conexión para '{alias}'; se omite.")
                continue

            if fmt in ("sql", "both"):
                log(f"⏳ Generando respaldos SQL por aplicación para {alias}...")
                creados += _dump_sql_por_app(db_url, alias, timestamp, carpeta, log)

            if fmt in ("json", "both"):
                log(f"⏳ Generando respaldos JSON por aplicación para {alias}...")
                creados += _dump_json_por_app(alias, timestamp, carpeta, log)

        elif "sqlite3" in engine:
            copia = _copiar_sqlite(alias, db_config, timestamp, carpeta, log)
            if copia:
                creados.append(copia)

    if creados:
        log(f"🎉 Backup terminado: {len(creados)} archivos en '{carpeta}'.")
    else:
        log("⚠️  No se generó ningún archivo de backup.")

    return creados


class Command(BaseCommand):
    help = (
        "Genera respaldos SQL (pg_dump) y JSON (dumpdata) separados por aplicación, "
        "además de una copia física de SQLite si aplica."
    )

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
        generar_backup(
            destino=options["destino"],
            fmt=options["format"],
            log=self.stdout.write,
        )
