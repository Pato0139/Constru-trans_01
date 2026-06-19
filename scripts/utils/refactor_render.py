#!/usr/bin/env python
"""
Script para analizar llamadas a render() en vistas de Django y verificar el uso de context.
"""
import ast
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def analyze_file(file_path):
    """Analiza un archivo Python para encontrar llamadas a render()."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        renders = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Verificar si es una llamada a render()
                if isinstance(node.func, ast.Name) and node.func.id == 'render':
                    # Obtener el número de línea
                    line_no = node.lineno
                    
                    # Verificar si tiene contexto (3er argumento o keyword)
                    has_dict_context = False
                    
                    # Context es usualmente el 3er argumento posicional
                    if len(node.args) >= 3:
                        if isinstance(node.args[2], ast.Dict):
                            has_dict_context = True
                    
                    # O podría ser un argumento keyword `context=...`
                    for kw in node.keywords:
                        if kw.arg == 'context' and isinstance(kw.value, ast.Dict):
                            has_dict_context = True
                    
                    renders.append((line_no, has_dict_context))
        
        return renders
    except Exception as e:
        return []


def main():
    print("Analizando vistas de Django...")
    print("=" * 80)
    
    # Directorios de aplicaciones
    apps_dir = BASE_DIR / 'apps'
    
    for app_dir in apps_dir.iterdir():
        if not app_dir.is_dir() or app_dir.name == '__pycache__':
            continue
        
        # Buscar archivos views.py
        views_files = list(app_dir.glob('**/views*.py'))
        
        for views_file in views_files:
            renders = analyze_file(views_file)
            
            if renders:
                correct = [r for r in renders if r[1]]
                incorrect = [r for r in renders if not r[1]]
                
                if incorrect:
                    print(f"[ALERTA] {views_file.relative_to(BASE_DIR)}: Tiene {len(renders)} render(s) en las líneas {[r[0] for r in renders]}.")
                else:
                    print(f"[OK] {views_file.relative_to(BASE_DIR)}: {len(renders)} render(s) correctos.")


if __name__ == "__main__":
    main()
