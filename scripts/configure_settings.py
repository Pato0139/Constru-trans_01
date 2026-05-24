#!/usr/bin/env python3
"""
Script para configurar settings.py para base de datos remota (Neon).
Se usa desde setup_windows.ps1 para evitar problemas de sintaxis en PowerShell.
"""
import os
import re
import sys

def configure_settings():
    base_dir = os.getcwd()
    settings_py = os.path.join(base_dir, 'core', 'settings.py')
    
    with open(settings_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    
    # Asegurar que DATABASES['remota'] esté presente
    if "DATABASES['remota'] = DATABASES['default'].copy()" not in content:
        # Buscar y reemplazar el patrón existente
        pattern = re.compile(r"(if DATABASE_URL:.*?# Agregar 'remota'.*?\n)", re.DOTALL)
        if pattern.search(content):
            # Ya tiene el comentario, agregar la línea si no existe
            pass
        else:
            # Agregar después de DATABASES['default']
            pattern = re.compile(r"(\s+DATABASES = \{[^}]+'default':[^}]+\})\s+(else:)", re.DOTALL)
            replacement = r"""\1
    # Agregar 'remota' usando la misma URL para sincronización
    DATABASES['remota'] = DATABASES['default'].copy()
\2"""
            new_content = pattern.sub(replacement, content)
            if new_content != content:
                content = new_content
                modified = True
    
    # Asegurar que DATABASE_ROUTERS esté configurado
    router_line = "DATABASE_ROUTERS = ['core.routers.EnrutadorInventario']"
    if router_line not in content:
        # Descomentar o reemplazar la línea
        content = re.sub(
            r'(# Desactivar router.*\n)?DATABASE_ROUTERS = \[\]',
            router_line,
            content
        )
        modified = True
    
    if modified:
        with open(settings_py, 'w', encoding='utf-8') as f:
            f.write(content)
        print('[OK] settings.py configurado para BD remota')
    else:
        print('[OK] settings.py ya estaba configurado')
    
    return 0

if __name__ == '__main__':
    sys.exit(configure_settings())