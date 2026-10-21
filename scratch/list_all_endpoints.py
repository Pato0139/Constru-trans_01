import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

resolver = get_resolver()

endpoints = []

def extract_patterns(patterns, prefix=""):
    for p in patterns:
        if isinstance(p, URLPattern):
            full_path = "/" + (prefix + str(p.pattern)).lstrip("^").rstrip("$")
            name = getattr(p, "name", None) or "-"
            callback = p.callback
            if hasattr(callback, "view_class"):
                view_name = callback.view_class.__name__
            elif hasattr(callback, "__name__"):
                view_name = callback.__name__
            else:
                view_name = str(callback)
            endpoints.append({
                "path": full_path,
                "name": name,
                "view": view_name,
            })
        elif isinstance(p, URLResolver):
            sub_prefix = prefix + str(p.pattern)
            extract_patterns(p.url_patterns, sub_prefix)

extract_patterns(resolver.url_patterns)

print(f"Total endpoints resueltos: {len(endpoints)}\n")
print(f"| # | Ruta URL | Nombre (Namespace / URL Name) | Vista / Handler |")
print(f"| :--- | :--- | :--- | :--- |")
for i, ep in enumerate(endpoints, 1):
    print(f"| {i} | `{ep['path']}` | `{ep['name']}` | `{ep['view']}` |")
