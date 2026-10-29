import os
import sys

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

import django
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT table_name, column_name 
    FROM information_schema.columns 
    WHERE data_type IN ('character varying', 'text') 
      AND table_schema = 'public'
""")
cols = cursor.fetchall()

found = []
for t, c in cols:
    try:
        cursor.execute(f'SELECT count(*) FROM "{t}" WHERE "{c}"::text ILIKE %s', ['%diego%'])
        cnt = cursor.fetchone()[0]
        if cnt > 0:
            cursor.execute(f'SELECT "{c}" FROM "{t}" WHERE "{c}"::text ILIKE %s LIMIT 3', ['%diego%'])
            vals = [r[0] for r in cursor.fetchall()]
            found.append((t, c, cnt, vals))
    except Exception as e:
        pass

print("RESULTS:")
for item in found:
    print(item)
