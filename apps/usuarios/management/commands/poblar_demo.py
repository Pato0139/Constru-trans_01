from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea catálogos y datos de demostración sin duplicarlos al repetir el comando."

    def add_arguments(self, parser):
        from django.conf import settings

        parser.add_argument("--restablecer-accesos", action="store_true", help="Activa y restablece la contraseña de las tres cuentas de acceso demo.")
        parser.add_argument(
            "--database",
            choices=tuple(settings.DATABASES),
            default="local",
            help="Base a poblar (por defecto, la base SQLite local).",
        )

    def handle(self, *args, **options):
        database = options["database"]
        self.stdout.write(self.style.NOTICE("Cargando catálogos de demostración..."))
        call_command("seed_tipos_material", database=database, stdout=self.stdout)

        self.stdout.write(self.style.NOTICE("Cargando usuarios, inventario y pedidos de demo..."))
        call_command("seed_data", database=database, stdout=self.stdout)

        if options.get("restablecer_accesos"):
            from django.db import transaction
            from apps.usuarios.models import Usuario, Conductor
            from .seed_data import DEFAULT_PASSWORD

            with transaction.atomic(using=database):
                for username, rol in (("Edward_Fonseca", "admin"), ("carlos_chofer", "conductor"), ("constructora_alfa", "cliente")):
                    usuario = Usuario.objects.using(database).get(username=username)
                    usuario.rol = rol
                    usuario.estado = "activo"
                    usuario.is_active = True
                    usuario.set_password(DEFAULT_PASSWORD)
                    usuario.save(using=database)
                    if rol == "conductor":
                        perfil, _ = Conductor.ensure_for_user(usuario, using=database)
                        perfil.estado = "activo"
                        perfil.save(using=database)
                    self.stdout.write(f"Acceso {rol}: {username} / {DEFAULT_PASSWORD}")

        self.stdout.write(
            self.style.SUCCESS(
                "Datos de demostración listos. Puedes ejecutar poblar_demo otra vez "
                "sin crear registros duplicados."
            )
        )
