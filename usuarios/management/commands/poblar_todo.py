from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Puebla catálogos base, demo funcional y centro de ayuda"

    def add_arguments(self, parser):
        parser.add_argument("--skip-demo", action="store_true")
        parser.add_argument("--skip-ayuda", action="store_true")
        parser.add_argument("--force-pedidos", action="store_true")

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("== Iniciando poblamiento total =="))

        self.stdout.write(self.style.NOTICE("1) Tipos de material"))
        call_command("seed_tipos_material")

        if not options["skip_demo"]:
            self.stdout.write(self.style.NOTICE("2) Datos demo principales"))
            call_command("seed_data", force_pedidos=options["force_pedidos"])

        if not options["skip_ayuda"]:
            self.stdout.write(self.style.NOTICE("3) Centro de ayuda"))
            call_command("seed_ayuda")

        self.stdout.write(self.style.SUCCESS("✅ Poblamiento total completado"))
