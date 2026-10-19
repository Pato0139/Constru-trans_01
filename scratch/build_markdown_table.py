import json
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
import django
django.setup()

from config.middleware import (
    _NAMESPACE_ROLES,
    _USUARIOS_URLNAMES_ROLES,
    _PEDIDOS_URLNAMES_ROLES,
    _LOGISTICA_URLNAMES_ROLES,
    _URLNAMES_BY_ROLE_EXTRA
)

with open('inventory_analyzed.json', 'r', encoding='utf-8') as f:
    endpoints = json.load(f)

# Priority mapping
priority_map = {
    'pagos': (1, '1. MÓDULO PAGOS'),
    'usuarios': (2, '2. MÓDULO USUARIOS Y PERFIL'),
    'compras': (3, '3. MÓDULO COMPRAS Y PROVEEDORES'),
    'logistica': (4, '4. MÓDULO CONDUCTORES Y VEHÍCULOS (LOGÍSTICA)'),
    'catalogo': (5, '5. MÓDULO CATÁLOGO Y MATERIALES'),
    'facturas': (6, '6. MÓDULO FACTURAS Y REPORTES'),
    'reportes': (6, '6. MÓDULO FACTURAS Y REPORTES'),
    'ia': (7, '7. MÓDULO ASISTENTE IA'),
    'pedidos': (8, '8. MÓDULO PEDIDOS'),
    'admin': (9, '9. DJANGO ADMIN'),
    'ayuda': (10, '10. MÓDULO AYUDA Y OTROS'),
    'licensing': (11, '11. MÓDULO LICENSING'),
    'config': (12, '12. MÓDULO CORE / CONFIG')
}

def resolve_role(ep):
    url = ep['url'].strip('/')
    parts = url.split('/')
    ns = parts[0] if parts else 'inicio'
    url_name = ep.get('name') or ''

    # Check url name specific role
    if ns == 'usuarios' and url_name in _USUARIOS_URLNAMES_ROLES:
        return ', '.join(sorted(_USUARIOS_URLNAMES_ROLES[url_name]))
    if ns in _URLNAMES_BY_ROLE_EXTRA and url_name in _URLNAMES_BY_ROLE_EXTRA[ns]:
        return ', '.join(sorted(_URLNAMES_BY_ROLE_EXTRA[ns][url_name]))

    # Check namespace role
    if ns in _NAMESPACE_ROLES:
        return ', '.join(sorted(_NAMESPACE_ROLES[ns]))

    if ep.get('role') and ep['role'] != 'No especificado (revisar middleware)':
        return ep['role']

    return 'Público / Autenticado'

def get_group(ep):
    url = ep['url']
    module = ep['module']
    if 'pagos' in module or url.startswith('pagos/'):
        if 'facturas' in url:
            return 'facturas'
        return 'pagos'
    if 'usuarios' in module or url.startswith('usuarios/'):
        return 'usuarios'
    if 'clientes' in module or url.startswith('clientes/'):
        return 'usuarios'
    if 'compras' in module or url.startswith('compras/'):
        return 'compras'
    if 'logistica' in module or url.startswith('logistica/'):
        return 'logistica'
    if 'catalogo' in module or url.startswith('catalogo/'):
        return 'catalogo'
    if 'reportes' in module or url.startswith('reportes/'):
        return 'reportes'
    if 'ia' in module or url.startswith('ia/'):
        return 'ia'
    if 'pedidos' in module or url.startswith('pedidos/'):
        return 'pedidos'
    for k in priority_map:
        if k in module or url.startswith(k + '/'):
            return k
    return 'config'

grouped = {}
for ep in endpoints:
    grp = get_group(ep)
    grouped.setdefault(grp, []).append(ep)

lines = []
lines.append('# INVENTARIO COMPLETO DE ENTRADAS DE DATOS (ÁREA 1)')
lines.append('')
lines.append('> **Auditoría de Seguridad Django — Fase 2: Backend como Única Fuente de Verdad**')
lines.append('> Criterios: URL, vista, rol permitido, campos aceptados, validación backend, validación solo frontend, y verificación de paso por `StrictModelForm` / `StrictForm`.')
lines.append('')

for grp_key in sorted(grouped.keys(), key=lambda k: priority_map.get(k, (99, ''))[0]):
    order, title = priority_map.get(grp_key, (99, grp_key.upper()))
    group_items = grouped[grp_key]
    lines.append(f'## {title}')
    lines.append('')
    lines.append('| URL | Vista (`archivo:línea`) | Rol Permitido | Campos / Parámetros que acepta | Val. Backend | Val. Solo Frontend | Pasa por StrictForm? |')
    lines.append('|---|---|---|---|:---:|:---:|:---:|')

    for ep in group_items:
        url = '/' + ep['url'].lstrip('/')
        vista_ref = f"`{ep['callback_name']}` (`{ep['file'].replace('\\', '/')}:{ep['line']}`)"
        rol = resolve_role(ep)
        
        # Accepted fields
        accepted = []
        if ep['query_params']:
            accepted.append('**GET**: `' + '`, `'.join(ep['query_params']) + '`')
        if ep['forms_used']:
            accepted.append('**Form**: ' + ', '.join(f'`{f}`' for f in ep['forms_used']))
        if ep['body_fields']:
            accepted.append('**Body/POST**: `' + '`, `'.join(ep['body_fields']) + '`')
        if ep['accepts_files']:
            accepted.append('**Archivos**: `request.FILES`')
        
        import re
        url_params = re.findall(r'<[a-zA-Z0-9_:]+>', url)
        if url_params:
            accepted.append('**URL**: `' + '`, `'.join(url_params) + '`')

        accepted_str = '<br>'.join(accepted) if accepted else 'Ninguno (Lectura estática)'

        # Strict check
        strict_col = ep['strict_status']
        if strict_col == 'Sí':
            strict_badge = '✅ Sí'
        elif strict_col == 'Parcial':
            strict_badge = '⚠️ Parcial'
        elif strict_col == 'No':
            strict_badge = '❌ **NO**'
        else:
            strict_badge = '➖ N/A'

        # Backend validation assessment
        if ep['strict_status'] == 'Sí':
            val_backend = 'Sí (Estricta)'
            val_front_only = 'No'
        elif ep['strict_status'] == 'Parcial':
            val_backend = 'Parcial'
            val_front_only = '⚠️ Sí'
        elif ep['strict_status'] == 'No':
            val_backend = 'Parcial / Débil'
            val_front_only = '⚠️ Sí'
        else:
            if ep['methods'] == ['GET'] and not ep['query_params']:
                val_backend = 'N/A (Lectura)'
                val_front_only = 'No'
            elif ep['body_fields'] or ep['query_params']:
                val_backend = 'Parcial / Manual'
                val_front_only = '⚠️ Sí'
            else:
                val_backend = 'N/A'
                val_front_only = 'No'

        lines.append(f'| `{url}` | {vista_ref} | `{rol}` | {accepted_str} | {val_backend} | {val_front_only} | {strict_badge} |')

    lines.append('')

output_content = '\n'.join(lines)
output_path = os.path.join(r'C:\Users\User\.gemini\antigravity-ide\brain\497143e7-7203-42a5-bcc3-955b35dc3ac6', 'inventario_seguridad_area1.md')
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(output_content)

print(f'Report written to {output_path}')
