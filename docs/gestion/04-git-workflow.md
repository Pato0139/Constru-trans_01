# Git Workflow Oficial

## Estrategia de Ramas
| Rama | Propósito | Origen | Merge a |
|------|-----------|--------|---------|
| `main` | Código estable y listo para producción | - | - |
| `edward/*` o `feature/*` | Nuevas funcionalidades y correcciones | `main` | `main` (mediante Pull Request) |

---

## Flujo de Trabajo
1. **Actualizar main**: `git checkout main && git pull origin main`
2. **Crear rama de feature**: `git checkout -b edward/nombre-feature`
3. **Desarrollar y commitear**:
   - Hacer commits frecuentes
   - Usar conventional commits
4. **Push y Pull Request**:
   - `git push origin edward/nombre-feature`
   - Crear PR en GitHub/GitLab hacia `main`
   - Asegurar que CI pase (`ruff check .` y `pytest`)
5. **Merge y limpiar**:
   - Después de aprobar el PR, mergearlo a main
   - `git checkout main && git pull origin main`
   - `git branch -d edward/nombre-feature`

---

## Convención de Commits (Conventional Commits)
| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `feat:` | Nueva funcionalidad | `feat: agregar chat IA` |
| `fix:` | Corrección de bug | `fix: corregir cálculo de total de pedido` |
| `docs:` | Actualización de documentación | `docs: actualizar README y guías` |
| `style:` | Formato, espaciado, etc. (sin cambio en funcionalidad) | `style: formatear código con ruff` |
| `refactor:` | Refactorización sin cambio en funcionalidad | `refactor: reorganizar views de usuarios` |
| `test:` | Agregar o corregir tests | `test: agregar tests para usuarios` |
| `chore:` | Mantenimiento, dependencias, etc. | `chore: actualizar dependencias` |

---

## Validaciones Pre-Merge
- ✅ `ruff check .` pasa sin errores
- ✅ `pytest` pasa todas las pruebas
- ✅ No hay conflictos con `main`
- ✅ Código revisado (si es un proyecto con equipo)

---

## CI/CD
El workflow `.github/workflows/ci.yml` se ejecuta en:
- Push a `main`, `develop`, `edward/*` y `feature/*`
- Cualquier Pull Request

Jobs ejecutados:
1. `ruff check .`: Linting del código
2. `pytest`: Pruebas unitarias
