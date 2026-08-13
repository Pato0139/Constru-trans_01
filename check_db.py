import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connection

print("BASE DE DATOS:", connection.settings_dict['NAME'])
print("HOST:", connection.settings_dict['HOST'])

with connection.cursor() as cursor:
    cursor.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'pedido' ORDER BY column_name;"
    )
    print("\nCOLUMNAS DE LA TABLA 'pedido':")
    for row in cursor.fetchall():
        print(" -", row[0])