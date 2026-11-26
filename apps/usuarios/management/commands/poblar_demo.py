from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea catálogos y datos de demostración sin duplicarlos al repetir el comando."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Cargando catálogos de demostración..."))
        call_command("seed_tipos_material", database="default", stdout=self.stdout)

        self.stdout.write(self.style.NOTICE("Cargando usuarios, inventario y pedidos de demo..."))
        call_command("seed_data", database="default", stdout=self.stdout)

        self.stdout.write(
            self.style.SUCCESS(
                "Datos de demostración listos. Puedes ejecutar poblar_demo otra vez "
                "sin crear registros duplicados."
            )
        )
