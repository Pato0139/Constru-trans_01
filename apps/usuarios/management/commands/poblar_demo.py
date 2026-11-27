from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea catálogos y datos de demostración sin duplicarlos al repetir el comando."

    def add_arguments(self, parser):
        from django.conf import settings

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

        self.stdout.write(
            self.style.SUCCESS(
                "Datos de demostración listos. Puedes ejecutar poblar_demo otra vez "
                "sin crear registros duplicados."
            )
        )
