
from django.core.management.base import BaseCommand
from apps.usuarios.models import Rol, MetodoPago


class Command(BaseCommand):
    help = "Carga datos iniciales para Rol y MetodoPago según el MER."

    def handle(self, *args, **options):
        # Roles
        roles_base = ['admin', 'conductor', 'cliente', 'empleado']
        for r in roles_base:
            obj, creado = Rol.objects.get_or_create(nombre_rol=r)
            if creado:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Rol creado: {r}"))

        # Métodos de pago
        metodos_base = [
            ('EFE', 'Efectivo'),
            ('TRA', 'Transferencia'),
            ('TAR', 'Tarjeta'),
            ('NEQ', 'Nequi'),
        ]
        for cod, met in metodos_base:
            obj, creado = MetodoPago.objects.get_or_create(
                codigo_metodo_pago=cod,
                defaults={'metodo': met}
            )
            if creado:
                self.stdout.write(self.style.SUCCESS(f"  ✓ Método creado: {met}"))

        self.stdout.write(self.style.SUCCESS("\n✅ Seed MER completado."))
