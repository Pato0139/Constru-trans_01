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

        self.stdout.write(self.style.NOTICE("1) Métodos de pago"))
        call_command("seed_mer")

        self.stdout.write(self.style.NOTICE("2) Tipos de material"))
        # Check if seed_tipos_material exists, if not skip or use whatever is available
        try:
            call_command("seed_tipos_material")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"⚠️  seed_tipos_material no disponible: {e}"))

        if not options["skip_demo"]:
            self.stdout.write(self.style.NOTICE("3) Datos demo principales"))
            call_command(
                "poblar_demo",
                admins=2,
                clientes=12,
                conductores=6,
                empleados=4,
                compras=8,
                solicitudes=8,
                pedidos=10,
            )

            self.stdout.write(self.style.NOTICE("4) Ajustes extra de demo"))
            call_command("seed_data", force_pedidos=options["force_pedidos"])
            call_command("llenar_datos_prueba")

        if not options["skip_ayuda"]:
            self.stdout.write(self.style.NOTICE("5) Centro de ayuda"))
            call_command("seed_ayuda")

        self.stdout.write(self.style.SUCCESS("✅ Poblamiento total completado"))
