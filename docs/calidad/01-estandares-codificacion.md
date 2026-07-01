# Estándares de Codificación y Nomenclatura

## Lenguaje del código

- Modelos, vistas, formularios y lógica de negocio: español del dominio del proyecto
- Convención técnica de Python: `snake_case`, `PascalCase`, `UPPER_SNAKE_CASE`
- Templates: `snake_case.html`
- Documentación formal: español
- URLs: expresivas y coherentes con el módulo, en español cuando aplica

---

## Nomenclatura
| Tipo | Convención | Ejemplo |
|------|-------------|---------|
| **Clases (Models, Views, Forms)** | PascalCase | `MaterialConstruccion`, `UsuarioForm`, `RegistroView` |
| **Funciones y Métodos** | snake_case | `calcular_total()`, `get_stock_actual()` |
| **Variables** | snake_case | `cantidad_actual`, `precio_total` |
| **Constantes** | UPPER_SNAKE_CASE | `ESTADO_ACTIVO`, `MAX_STOCK` |
| **Templates** | snake_case.html | `mis_pedidos.html`, `editar_perfil.html` |
| **URLs** | snake_case con guiones | `/usuarios/perfil/editar/`, `/inventario/materiales/` |
| **Campos de Modelo** | snake_case | `codigo_pedido`, `fecha_registro` |

---

## Linting y Formato
- Se usa **Ruff** para linting y formato
- Configuración en `pyproject.toml`
- Reglas: `E`, `F`, `W`, `I`, `N`, `B`, `DJ`
- Ignora: `E501` (línea demasiado larga)
- Target version: Python 3.12
- Comandos útiles:
  - `ruff check .`: revisar errores
  - `ruff format .`: formatear código automáticamente

---

## Estructura de Tests
Cada app tiene una carpeta `tests/` con:
- `test_models.py`: Pruebas de modelos y métodos
- `test_views.py`: Pruebas de vistas y templates
- `test_forms.py`: Pruebas de formularios
- `test_permissions.py`: Pruebas de permisos y autenticación (si aplica)
