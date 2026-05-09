#!/usr/bin/env python
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.usuarios.models import Material, Stock

print('=== Agregando stock a los materiales ===')
for m in Material.objects.all():
    try:
        s, created = Stock.objects.get_or_create(material=m)
        if created or s.cantidad <= 0:
            s.cantidad = 100
            s.save()
            print(f'- {m.nombre}: Stock actualizado a 100 unidades')
        else:
            print(f'- {m.nombre}: Ya tiene {s.cantidad} unidades')
    except Exception as e:
        print(f'- Error con {m.nombre}: {e}')

print('=== Listo! ===')
