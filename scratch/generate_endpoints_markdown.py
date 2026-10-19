import os
import sys

sys.path.insert(0, os.getcwd())
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

resolver = get_resolver()
eps = []

def extract(patterns, prefix=''):
    for p in patterns:
        if isinstance(p, URLPattern):
            path = '/' + (prefix + str(p.pattern)).lstrip('^').rstrip('$')
            if not path.startswith('/admin/'):
                name = getattr(p, 'name', '-') or '-'
                cb = p.callback
                if hasattr(cb, 'view_class'):
                    vname = cb.view_class.__name__
                elif hasattr(cb, '__name__'):
                    vname = cb.__name__
                else:
                    vname = str(cb)
                eps.append((path, name, vname))
        elif isinstance(p, URLResolver):
            sub = prefix + str(p.pattern)
            if not sub.startswith('admin/'):
                extract(p.url_patterns, sub)

extract(resolver.url_patterns)

with open('scratch/endpoints_table.md', 'w', encoding='utf-8') as f:
    f.write(f"### Inventario Exhaustivo de Endpoints de la Aplicación ({len(eps)} Rutas)\n\n")
    f.write("| # | Ruta (URL Pattern) | Nombre de Ruta (URL Name) | Vista / Controlador Asociado |\n")
    f.write("| :--- | :--- | :--- | :--- |\n")
    for i, (path, name, vname) in enumerate(eps, 1):
        f.write(f"| {i} | `{path}` | `{name}` | `{vname}` |\n")

print(f"Generado scratch/endpoints_table.md con {len(eps)} endpoints.")
