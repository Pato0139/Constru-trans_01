import json
import os
import sys

with open('inventory_analyzed.json', 'r', encoding='utf-8') as f:
    endpoints = json.load(f)

# Priority mapping
priority_map = {
    'pagos': (1, '1. MÓDULO PAGOS'),
    'usuarios': (2, '2. MÓDULO USUARIOS Y PERFIL'),
    'clientes': (2, '2. MÓDULO USUARIOS Y PERFIL (CLIENTES)'),
    'compras': (3, '3. MÓDULO COMPRAS Y PROVEEDORES'),
    'logistica': (4, '4. MÓDULO CONDUCTORES Y VEHÍCULOS (LOGÍSTICA)'),
    'catalogo': (5, '5. MÓDULO CATÁLOGO Y MATERIALES'),
    'facturas': (6, '6. MÓDULO FACTURAS Y REPORTES'),
    'reportes': (6, '6. MÓDULO FACTURAS Y REPORTES'),
    'ia': (7, '7. MÓDULO ASISTENTE IA'),
    'pedidos': (8, '8. MÓDULO PEDIDOS'),
    'ayuda': (9, '9. MÓDULO AYUDA Y OTROS'),
    'licensing': (9, '9. MÓDULO LICENSING'),
    'config': (10, '10. MÓDULO CORE / CONFIG')
}

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

# Output detailed summary
print(f'Total endpoints grouped: {len(endpoints)}')
for grp_key in sorted(grouped.keys(), key=lambda k: priority_map.get(k, (99, ''))[0]):
    order, title = priority_map.get(grp_key, (99, grp_key.upper()))
    print(f'{title}: {len(grouped[grp_key])} endpoints')
