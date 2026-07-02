#!/usr/bin/env python
"""Debug script para verificar en cuál BD están las unidades."""

import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from usuarios.models import UnidadMedida

print("\n=== VERIFICACIÓN DE BASES DE DATOS ===\n")

default_count = UnidadMedida.objects.using("default").count()
print(f"BD 'default': {default_count} unidades")
if default_count > 0:
    for u in UnidadMedida.objects.using("default").order_by("orden"):
        print(f"  - {u.codigo:10} {u.nombre}")

try:
    remota_count = UnidadMedida.objects.using("remota").count()
    print(f"\nBD 'remota': {remota_count} unidades")
    if remota_count > 0:
        for u in UnidadMedida.objects.using("remota").order_by("orden"):
            print(f"  - {u.codigo:10} {u.nombre}")
except Exception as e:
    print(f"\nBD 'remota': Error - {e}")

print("\n=== ROUTER ACTUAL ===")
from core.db_preference import debe_usar_bd_remota, get_db_preference
print(f"Preferencia actual: {get_db_preference()}")
print(f"Debe usar BD remota: {debe_usar_bd_remota()}")
