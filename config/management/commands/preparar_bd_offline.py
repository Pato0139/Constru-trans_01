import json
import logging
import tempfile
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connections

from config.utils import conexion_remota_disponible

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Prepara una copia local inicial de Neon para trabajar sin conexión."

    def handle(self, *args, **options):
        if "local" not in settings.DATABASES:
            return

        db_name = settings.DATABASES["local"].get("NAME")
        if str(db_name) == ":memory:":
            return

        marker = Path(f"{db_name}.offline-ready")
        try:
            self._repair_empty_migration_history()
            call_command("migrate", database="local", interactive=False, verbosity=0)
        except Exception:
            logger.exception("No se pudieron preparar las tablas locales para modo offline.")
            raise

        copia_parcial = marker.exists() and marker.read_text(encoding="utf-8").startswith(
            "Copia parcial:"
        )
        if marker.exists() and not copia_parcial:
            self.stdout.write("La base local offline ya está preparada.")
            return

        if "remota" not in settings.DATABASES or not conexion_remota_disponible():
            self.stdout.write(
                self.style.WARNING(
                    "Neon no está disponible. Se conservará la base local existente."
                )
            )
            return

        if self._hay_datos_locales():
            marker.write_text("Base local preexistente; se conservó para proteger sus datos.\n")
            self.stdout.write(
                self.style.WARNING(
                    "La base local ya contiene datos; no se reemplazó con la copia de Neon."
                )
            )
            return

        backups_dir = Path(settings.BASE_DIR) / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        fixture_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".json",
                prefix="offline-snapshot-",
                dir=backups_dir,
                delete=False,
            ) as fixture:
                fixture_path = Path(fixture.name)
                call_command(
                    "dumpdata",
                    database="remota",
                    exclude=[
                        "admin.logentry",
                        "sessions.session",
                        # Estas tablas remotas contienen filas legacy inválidas
                        # para el esquema local actual.
                        "pagos",
                        "ia",
                    ],
                    format="json",
                    indent=2,
                    stdout=fixture,
                    verbosity=0,
                )

            self._sanitize_fixture(fixture_path)
            self._clear_local_auth_catalogs()
            call_command("loaddata", str(fixture_path), database="local", verbosity=0)
            marker.write_text("Copia inicial de Neon descargada correctamente.\n")
            self.stdout.write(self.style.SUCCESS("Copia local preventiva descargada desde Neon."))
        except Exception:
            logger.exception("Falló la descarga de la copia preventiva de Neon.")
            try:
                usuarios_copiados = self._download_users()
            except Exception:
                logger.exception("Tampoco se pudieron copiar los usuarios para el modo offline.")
                self.stderr.write(
                    self.style.WARNING(
                        "No se pudo completar la copia offline ni copiar las cuentas locales."
                    )
                )
            else:
                if usuarios_copiados:
                    marker.write_text(
                        "Copia parcial: cuentas locales descargadas; datos operativos no copiados.\n"
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            "Copia completa incompatible; se descargaron las cuentas para permitir "
                            "el inicio de sesión offline."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "No se encontraron cuentas remotas para copiar a la base local."
                        )
                    )
        finally:
            if fixture_path:
                try:
                    fixture_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("No se pudo quitar el archivo temporal %s", fixture_path)

    @staticmethod
    def _hay_datos_locales():
        apps_sin_datos_operativos = {"sessions", "admin", "contenttypes"}
        user_model = get_user_model()
        for model in apps.get_models():
            if model is user_model or model._meta.app_label in apps_sin_datos_operativos:
                continue
            if model._meta.label == "auth.Permission":
                continue
            try:
                if model.objects.using("local").exists():
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _download_users():
        user_model = get_user_model()
        local_users = user_model.objects.using("local")
        if local_users.exists():
            return 0

        usuarios = []
        for remoto in user_model.objects.using("remota").iterator(chunk_size=500):
            usuarios.append(
                user_model(
                    **{
                        field.attname: getattr(remoto, field.attname)
                        for field in user_model._meta.concrete_fields
                    }
                )
            )

        if usuarios:
            user_model.objects.using("local").bulk_create(usuarios, batch_size=500)
        return len(usuarios)

    @staticmethod
    def _sanitize_fixture(fixture_path):
        with fixture_path.open(encoding="utf-8") as fixture:
            records = json.load(fixture)

        excluded_apps = {"pagos", "ia"}
        records = [record for record in records if record["model"].split(".", 1)[0] not in excluded_apps]

        changed = True
        while changed:
            changed = False
            available = {}
            for record in records:
                model = apps.get_model(record["model"])
                available.setdefault(model, set()).add(record.get("pk"))
                for field in model._meta.concrete_fields:
                    if field.primary_key or not field.is_relation or field.target_field.primary_key:
                        continue
                    if field.name in record["fields"]:
                        available.setdefault((model, field.name), set()).add(
                            record["fields"][field.name]
                        )

            kept = []
            for record in records:
                model = apps.get_model(record["model"])
                values = record["fields"]
                invalid = False
                for field in model._meta.concrete_fields:
                    if field.primary_key:
                        continue
                    value = values.get(field.name)
                    if value is None and not field.null:
                        invalid = True
                        break
                    if value is not None and field.is_relation and field.many_to_one:
                        target_model = field.remote_field.model
                        target_field = field.target_field
                        candidates = available.get(target_model, set())
                        if not target_field.primary_key:
                            candidates = available.get((target_model, target_field.name), set())
                        if value not in candidates:
                            invalid = True
                            break
                if not invalid:
                    for field in model._meta.many_to_many:
                        if field.name not in values:
                            continue
                        target_model = field.remote_field.model
                        valid_ids = available.get(target_model, set())
                        values[field.name] = [
                            item for item in values[field.name] if item in valid_ids
                        ]
                    kept.append(record)
                else:
                    changed = True
            records = kept

        with fixture_path.open("w", encoding="utf-8") as fixture:
            json.dump(records, fixture, ensure_ascii=False)

    @staticmethod
    def _clear_local_auth_catalogs():
        user_model = get_user_model()
        group_model = apps.get_model("auth", "Group")
        permission_model = apps.get_model("auth", "Permission")
        content_type_model = apps.get_model("contenttypes", "ContentType")
        tables_to_clear = [
            user_model._meta.get_field("groups").m2m_db_table(),
            user_model._meta.get_field("user_permissions").m2m_db_table(),
            group_model._meta.get_field("permissions").m2m_db_table(),
            group_model._meta.db_table,
            permission_model._meta.db_table,
            content_type_model._meta.db_table,
        ]
        with connections["local"].cursor() as cursor:
            for table in dict.fromkeys(tables_to_clear):
                cursor.execute(f'DELETE FROM "{table}"')

    @staticmethod
    def _repair_empty_migration_history():
        connection = connections["local"]
        tables = set(connection.introspection.table_names())
        user_model = apps.get_model(settings.AUTH_USER_MODEL)
        if user_model._meta.db_table in tables:
            return

        app_tables = tables - {"django_migrations", "sqlite_sequence"}
        if app_tables:
            raise CommandError(
                "La base local tiene un esquema parcial y no se modificó para evitar perder datos. "
                "Ejecuta una reparación respaldada de la base local."
            )

        if "django_migrations" in tables:
            # Versiones anteriores registraron migraciones que el router local
            # había omitido. Si no existe ninguna tabla de aplicación, limpiar
            # solo ese historial permite crear el esquema completo con migrate.
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM django_migrations")
