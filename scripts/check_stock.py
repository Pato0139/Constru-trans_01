#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.usuarios.models import Material, Stock

print('=== Materiales y su Stock ===')
for m in Material.objects.all():
    try:
        s = m.stock_info
        print(f'- {m.nombre}: {s.cantidad} unidades')
    except Exception as e:
        print(f'- {m.nombre}: SIN STOCK o error: {e}')
