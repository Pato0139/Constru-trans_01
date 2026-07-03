import os
import sys

import django

# Add the project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps", "business_django"))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings.base")
django.setup()

from usuarios.models import MetodoPago

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
        print(f"Creado: {codigo} - {nombre}")
    else:
        print(f"Ya existe: {codigo} - {nombre}")

print(f"\nTerminado! Creados {creados} métodos de pago nuevos.")
