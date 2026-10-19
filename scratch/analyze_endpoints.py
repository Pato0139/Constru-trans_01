import os
import sys
import inspect
import json
import re

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver
from config.forms_base import StrictModelForm, StrictForm, StrictFormMixin
from django import forms
import importlib

# Map of all form classes to whether they are strict
form_strictness = {}
form_modules = [
    'apps.pagos.forms',
    'apps.pedidos.forms_pagos',
    'apps.pedidos.forms',
    'apps.usuarios.forms',
    'apps.compras.forms',
    'apps.logistica.forms',
    'apps.catalogo.forms',
    'apps.ayuda.forms',
]

for mod_name in form_modules:
    try:
        mod = importlib.import_module(mod_name)
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, (forms.Form, forms.ModelForm)):
                is_strict = issubclass(obj, (StrictModelForm, StrictForm, StrictFormMixin))
                form_strictness[name] = is_strict
    except Exception as e:
        pass

def get_app_endpoints(patterns, prefix=''):
    for p in patterns:
        if isinstance(p, URLPattern):
            mod = getattr(p.callback, '__module__', '')
            if mod.startswith('apps.') or mod.startswith('config.'):
                yield {
                    'url': prefix + str(p.pattern),
                    'name': p.name,
                    'callback_name': getattr(p.callback, '__name__', str(p.callback)),
                    'module': mod,
                    'callback': p.callback
                }
        elif isinstance(p, URLResolver):
            yield from get_app_endpoints(p.url_patterns, prefix + str(p.pattern))

resolver = get_resolver()
endpoints = list(get_app_endpoints(resolver.url_patterns))
print(f'Total custom endpoints: {len(endpoints)}')

analyzed = []
for ep in endpoints:
    cb = ep['callback']
    # unwrap all decorators
    unwrapped = inspect.unwrap(cb)
    
    # get source file and lines of unwrapped function
    try:
        src_file = inspect.getsourcefile(unwrapped) or inspect.getsourcefile(cb)
    except Exception:
        src_file = ''

    try:
        lines, start_line = inspect.getsourcelines(unwrapped)
    except Exception:
        try:
            lines, start_line = inspect.getsourcelines(cb)
        except Exception:
            lines, start_line = [], 0

    code = ''.join(lines) if lines else ''

    # Get decorators from raw source file if possible
    decorators = []
    if src_file and os.path.exists(src_file) and start_line > 0:
        try:
            with open(src_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_file_lines = f.readlines()
            idx = start_line - 1
            while idx > 0:
                prev = all_file_lines[idx - 1].strip()
                if prev.startswith('@'):
                    decorators.insert(0, prev)
                    idx -= 1
                elif prev == '' or prev.startswith('#'):
                    idx -= 1
                else:
                    break
        except Exception:
            pass

    dec_str = ' '.join(decorators)
    role = 'Público / Autenticado'
    if 'admin_required' in dec_str:
        role = 'admin'
    elif 'role_required' in dec_str:
        m = re.search(r'role_required\(\[([^\]]+)\]\)', dec_str)
        role = m.group(1).replace('"', '').replace("'", '').strip() if m else 'role_required'
    elif 'login_required' in dec_str:
        role = 'Autenticado'
    elif 'superuser' in code or 'is_superuser' in code:
        role = 'superuser'

    methods = ['GET']
    if 'require_POST' in dec_str:
        methods = ['POST']
    elif 'require_http_methods' in dec_str:
        m = re.search(r'require_http_methods\(\[([^\]]+)\]\)', dec_str)
        if m:
            methods = [x.strip().replace('"', '').replace("'", '') for x in m.group(1).split(',')]
    elif 'request.method == "POST"' in code or "request.method == 'POST'" in code:
        methods = ['GET', 'POST']

    accepts_files = 'request.FILES' in code

    form_matches = re.findall(r'([A-Za-z0-9_]+Form)\(', code)
    forms_used = list(dict.fromkeys(form_matches))

    qp = re.findall(r'request\.GET\.get\([\'"]([a-zA-Z0-9_\-]+)[\'"]', code)
    query_params = list(dict.fromkeys(qp))

    json_fields = re.findall(r'data\.get\([\'"]([a-zA-Z0-9_\-]+)[\'"]', code)
    post_fields = re.findall(r'request\.POST\.get\([\'"]([a-zA-Z0-9_\-]+)[\'"]', code)
    body_fields = list(dict.fromkeys(json_fields + post_fields))

    strict_status = 'N/A'
    if forms_used:
        strict_list = [form_strictness.get(fn, False) for fn in forms_used]
        if all(strict_list):
            strict_status = 'Sí'
        elif any(strict_list):
            strict_status = 'Parcial'
        else:
            strict_status = 'No'

    rel_file = os.path.relpath(src_file, os.getcwd()) if src_file and os.path.isabs(src_file) and os.getcwd() in src_file else (src_file or '')
    rel_file = rel_file.replace('\\', '/')

    analyzed.append({
        'url': ep['url'],
        'name': ep['name'],
        'callback_name': getattr(unwrapped, '__name__', ep['callback_name']),
        'module': getattr(unwrapped, '__module__', ep['module']),
        'file': rel_file,
        'line': start_line,
        'role': role,
        'methods': methods,
        'decorators': decorators,
        'forms_used': forms_used,
        'strict_status': strict_status,
        'accepts_files': accepts_files,
        'query_params': query_params,
        'body_fields': body_fields,
    })

with open('inventory_analyzed.json', 'w', encoding='utf-8') as f:
    json.dump(analyzed, f, indent=2, ensure_ascii=False)

print(f'Successfully analyzed {len(analyzed)} unwrapped endpoints into inventory_analyzed.json')
