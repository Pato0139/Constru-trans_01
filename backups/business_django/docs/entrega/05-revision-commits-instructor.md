# Revisión de ramas y commits — Instructor / equipo

## Ramas disponibles (remoto)

| Rama | Notas |
|------|--------|
| `main` | Rama principal integrada |
| `Revision-Instructor` | Rama mencionada por el instructor |
| `Edward_Fonseca` | Rama de trabajo actual |
| `ivan`, `Jhoanrr18`, `Juan`, `Michel-Perez` | Ramas de integrantes |

Comandos útiles:

```powershell
git fetch --all
git branch -a
git log --oneline --graph --all -20
git show <commit-id>
```

## Comparación Revision-Instructor vs main

En el estado analizado (junio 2026), `origin/Revision-Instructor` y `origin/main` comparten el mismo tip (`e1e879d`). No hay commits exclusivos pendientes de merge entre esas ramas en el remoto.

## Commits con impacto en usabilidad y correcciones pedidas

| Commit | Mensaje | Cambio observado | Impacto en el proyecto |
|--------|---------|------------------|------------------------|
| `e1e879d` | feat: core structure, models, user views | Estructura base Django y vistas de usuario | Base del sistema actual |
| `e4266db` | fix: relaciones y campos en pedidos | Modelo/vistas de pedidos alineados | Corrige errores al guardar y listar pedidos |
| `3ba7228` | fix: inventario, órdenes, middleware, signals | Signals recalculan total; licencias | Totales más consistentes |
| `d7feede` | fix: sidebar y estilos | Menú lateral reorganizado | Navegación admin (colapsables) |
| `3fbd2e6` | fix: diseño responsive | CSS adaptable | Usabilidad móvil |
| `027ff55` | fix: estética compras/proveedores | Colores y formularios compras | Legibilidad en módulo compras |
| `b249ca4` | fix: accesibilidad | Ajustes a11y | Contraste parcial |
| `d96f0b0` | stock, fechas, formularios | Validación fechas y stock | Menos errores al crear pedidos |
| `0b00544` | campos nulos, teléfonos | Formularios más flexibles | Menos rechazos al registrar |
| `80079c1` | solo BD remota en setup | Configuración Neon | Entorno unificado en equipo |

## Qué buscar al revisar un commit del instructor

```powershell
git show d7feede --stat
git show d7feede -- "*.css" "*.html"
```

Fijarse en:

- Cambios visuales (CSS, plantillas)
- Botones y colores
- Lógica de pedidos y totales
- Rutas nuevas en `urls.py`
- Validaciones en formularios

## Acción realizada en repositorio (Fase 1)

1. `.gitignore` ampliado: migraciones, `backups/*.json`
2. `git rm -r --cached` sobre carpetas `migrations` (se conservan en disco)
3. Reincorporados solo `migrations/__init__.py` (paquetes Python)
4. Eliminados del índice: `backups/db_backup_*.json`

**Commit sugerido** (cuando apruebes):

```
Corrige .gitignore y elimina migraciones y backups del repositorio
```
