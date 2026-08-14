from django.core.management.base import BaseCommand

from core.db_preference import PREF_LOCAL, clear_db_preference, set_db_preference
from usuarios.models import MetodoPago


class Command(BaseCommand):
    help = "Carga datos iniciales para MetodoPago según el MER."

    def handle(self, *args, **options):
        set_db_preference(PREF_LOCAL)
        try:
            metodos_base = [
                ("EFE", "Efectivo"),
                ("TRA", "Transferencia"),
                ("TAR", "Tarjeta"),
                ("NEQ", "Nequi"),
            ]
            for cod, met in metodos_base:
                obj, creado = MetodoPago.objects.get_or_create(
                    codigo_metodo_pago=cod, defaults={"metodo": met}
                )
                if creado:
                    self.stdout.write(self.style.SUCCESS(f"  [OK] Método creado: {met}"))
        finally:
            clear_db_preference()

        self.stdout.write(self.style.SUCCESS("\n[OK] Seed MER completado."))
