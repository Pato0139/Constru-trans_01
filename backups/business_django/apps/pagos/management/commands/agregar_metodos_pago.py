from django.core.management.base import BaseCommand

from apps.usuarios.models import MetodoPago


class Command(BaseCommand):
    help = "Agrega los métodos de pago comunes a la base de datos"

    def handle(self, *args, **kwargs):
        metodos_pago = [
            ("EFECTIVO", "Efectivo (Pago en persona)"),
            ("TRANSFERENCIA", "Transferencia Bancaria"),
            ("TARJETA_CREDITO", "Tarjeta de Crédito"),
            ("TARJETA_DEBITO", "Tarjeta de Débito"),
            ("PSE", "PSE - Pagos Seguros en Línea"),
            ("NEQUI", "Nequi"),
            ("DAVIPLATA", "DaviPlata"),
        ]

        creados = 0
        for codigo, nombre in metodos_pago:
            metodo, created = MetodoPago.objects.get_or_create(
                codigo_metodo_pago=codigo, defaults={"metodo": nombre}
            )
            if created:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Creado: {codigo} - {nombre}"))
            else:
                self.stdout.write(f"ℹ️  Ya existe: {codigo} - {nombre}")

        self.stdout.write(
            self.style.SUCCESS(f"\n🎉 Terminado! Creados {creados} métodos de pago nuevos.")
        )
