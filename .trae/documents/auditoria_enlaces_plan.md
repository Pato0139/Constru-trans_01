# Plan: Auditoría Completa + Blindaje de Botones, Paneles y Enlaces

## Contexto
El usuario reportó un `NoReverseMatch` en `/usuarios/panel/` al cargar `templates/partials/sidebar.html` porque el template seguía referenciando namespaces de apps obsoletas (`inventario`, `transporte`, `gestion_pedidos`, `historial`) tras la reestructuración de Fase 4.

Se solicita **examinar TODO el proyecto** para asegurar que **nunca** vuelva a pasar y dejar botones, paneles, enlaces, redirects y reverses en perfecto funcionamiento.

---

## Repository Research (Hallazgos de la Auditoría)

Se ejecutó una **auditoría AUTOMATIZADA** de doble vía:

1. **Inventario canónico de URLs registradas** — Se recorrió el `URLResolver` real de Django (`django.urls.get_resolver()`) para listar TODOS los namespaces + url_names que existen físicamente en el proyecto (incluyendo Django Admin):  
   Resultado: **226 URLs válidas**, entre ellas 85 de nuestras 12 apps (`usuarios`, `clientes`, `catalogo`, `compras`, `pedidos`, `logistica`, `auditoria`, `reportes`, `inicio`, `licensing`, `ayuda`, `ia`).

2. **Validación cruzada con el resolver** — Se extrajeron todas las referencias `{% url 'X:Y' %}` en templates (182 ocurrencias en 70 archivos HTML) y todos los `reverse()`/`redirect()`/`reverse_lazy()` en Python (130 ocurrencias en 21 archivos) y se intentó resolver cada una con `django.urls.reverse()`.

### ✅ Resultado de la auditoría de URLs
**No se encontró NINGÚN NoReverseMatch en nuestro código** tras los fixes aplicados en esta conversación.

Todos los issues detectados pertenecen a librerías de `venv/`:
- `django.contrib.admin` (placeholders `%s:%s_%s_changelist`)
- `simple_history`, `django_otp`, `rest_framework`, `debug_toolbar`
- Django templates de `registration/password_reset_email.html`: issue reportado era falso positivo — al pasar los kwargs correctos `uidb64=... token=...` el URL sí resuelve.

### ⚠️ Inconsistencias menores (no rompen, pero sí generan confusión)
Halladas manualmente tras la auditoría:

| Hallazgo | Descripción | Severidad |
|---|---|---|
| **Claves i18n en `static/js/user-preferences.js` L112, L194** | Aún hacen referencia a `sidebar.historial`; en la UI se cambió el namespace a `auditoria`. | Baja |
| **Carpetas estáticas con nombres antiguos** | `static/css/inventario/` y `static/css/ordenes/` aún existen (5 archivos CSS). No rompen URLs pero son confusas tras la reestructuración. | Baja |
| **Carpeta JS estática con nombre antiguo** | `static/js/inventario/` (3 archivos: catalogo-menu.js, materiales-ajax.js, movimientos.js). Los scripts dentro parecen no referenciar namespaces viejos, pero el nombre del directorio puede inducir errores. | Baja |

---

## Archivos y Módulos a Modificar

### Tarea A — Blindaje PROACTIVO (evita que el error vuelva a ocurrir)
- **Archivo NUEVO**: `core/tests/test_url_namespaces.py` — Test automático que valida todos los `{% url %}` en templates y todos los `reverse/redirect/reverse_lazy` en Python, fallando si alguna referencia no se resuelve.
- **Archivo**: `core/middleware.py` — Agregar un `_NAMESPACES_OBSOLETOS` con un chequeo en **modo DEBUG** que, al detectar un namespace obsoleto en `resolver_match.app_name` o una plantilla intente usarlo, emita un `logger.error` claro indicando la migración sugerida.

### Tarea B — Correcciones menores (consistencia)
- `static/js/user-preferences.js` (L112, L194): `sidebar.historial` → `sidebar.auditoria`
- Renombrar **carpetas**:
  - `static/css/inventario/` → `static/css/catalogo/`
  - `static/css/ordenes/` → `static/css/pedidos/`
  - `static/js/inventario/` → `static/js/catalogo/`
  - **Y actualizar las referencias `{% static %}`** en templates HTML y bases CSS que apunten a las rutas antiguas.

### Tarea C — Pruebas de humo de navegación (validación final)
- Añadir tests que prueben la carga HTTP exitosa de **cada página principal** con `usuario` de cada rol:
  - Admin: `/usuarios/panel/`, `/catalogo/materiales/`, `/catalogo/stock/`, `/catalogo/movimientos/`, `/catalogo/tipos/`, `/logistica/vehiculos/`, `/compras/`, `/compras/proveedores/`, `/pedidos/admin/lista/`, `/pedidos/entregas/`, `/auditoria/lista/`, `/reportes/admin/`, `/clientes/admin/lista/`, `/usuarios/usuarios/`, `/usuarios/conductores/`
  - Cliente: `/clientes/panel/`, `/clientes/mis-pedidos/`, `/clientes/pedido/crear/`, `/clientes/seguimiento/`, `/clientes/historial/`
  - Conductor: `/usuarios/panel-conductor/`, `/usuarios/pedidos-conductor/`, `/usuarios/mis-entregas/`

---

## Implementation Steps (orden de dependencias)

### Paso 1. Crear test blindaje de namespaces y URLs (Tarea A)
Crear `core/tests/test_url_namespaces.py` que:
1. Recorra todos los archivos `.html` del proyecto (excluyendo `venv/`) y extraiga `{% url 'X:Y' %}`.
2. Recorra todos los `.py` y extraiga cadenas pasadas a `reverse/reverse_lazy/redirect` de la forma `'X:Y'`.
3. Por cada referencia, intente `reverse()` con args/kwargs de prueba.
4. **Falle el test si encuentra algo que no resuelva.**
5. Además, valide que **las vistas referenciadas en cada URL existan** en su módulo `views.py` correspondiente (se confirmó en auditoría: 0 issues).

### Paso 2. Añadir detección de namespaces obsoletos al middleware (Tarea A)
En `core/middleware.py`:
- Declarar `_NAMESPACES_OBSOLETOS = {"inventario":"catalogo","transporte":"logistica","gestion_pedidos":"pedidos","novedades":"logistica","historial":"auditoria","ordenes":"pedidos"}`
- Al final de la capa `UsuarioRoleMiddleware.__call__`, **si `settings.DEBUG` es True**, comprobar si `resolver_match.app_name` está obsoleto y si algún template solicitado (del request) contiene refs obsoletas. Loguear `logger.error(f"Namespace OBSOLETO '{old}' detectado. Debe migrarse a '{new}' en {ubicacion}")`.

### Paso 3. Corregir consistencia en archivos JS/CSS y templates (Tarea B)
1. `static/js/user-preferences.js` L112 y L194: `sidebar.historial` → `sidebar.auditoria`
2. **Renombrar carpetas**:
   - `static/css/inventario/*` → `static/css/catalogo/*`
   - `static/css/ordenes/*` → `static/css/pedidos/*`
   - `static/js/inventario/*` → `static/js/catalogo/*`
3. **Buscar y actualizar** TODAS las referencias `{% static 'css/inventario/`, `{% static 'css/ordenes/`, `{% static 'js/inventario/` en templates HTML y reemplazarlas por las nuevas rutas.

### Paso 4. Añadir tests de humo HTTP (Tarea C)
Crear `core/tests/test_smoke_navigation.py`:
- Clases por rol: `TestAdminNavigation`, `TestClienteNavigation`, `TestConductorNavigation`.
- Por cada URL mapeada (de la lista de arriba), `self.client.get(url)` y `assertEqual(response.status_code, 200)` (o 302 si la vista hace redirect interno a login antes del middleware role, con `follow=True`).
- Usar `@override_settings(DEBUG=False)` o forzar `ALLOWED_HOSTS=['*']` para que `testserver` no cause 400.

### Paso 5. Validación final
Ejecutar en orden:
1. `py manage.py check` → 0 issues
2. `py -m pytest core/tests/test_url_namespaces.py -v` → PASSED
3. `py -m pytest core/tests/test_smoke_navigation.py -v` → PASSED (los que requieran BD se saltarán si no hay BD de test, pero al menos corren los que no hacen BD)
4. `py manage.py check --deploy` (opcional)
5. Levantar servidor y pulsar los botones críticos del sidebar/navbar.

---

## Dependencies and Considerations
- **Seguridad**: El middleware anti-obsoleto solo se activa con `DEBUG=True` para NO afectar rendimiento en producción.
- **Compatibilidad static**: Tras renombrar carpetas static, `collectstatic` (si se usa) tomará los nuevos nombres; no hay impacto sobre URLs de static porque los templates usan `{% static %}` que actualizaremos.
- **Coverage**: Las carpetas static viejas contaban con coverage en la configuración vieja (ya removida en pyproject.toml), así que no afecta tests.
- **Riesgo de los smoke tests**: Si no hay BD PostgreSQL disponible para tests, los tests que dependen de la BD pueden requerir `@pytest.mark.skipif(no_test_db)` o el uso de `pytest --create-db` de pytest-django.

---

## Validation
| Prueba | Resultado esperado |
|---|---|
| `py manage.py check` | 0 issues |
| `pytest core/tests/test_url_namespaces.py` | PASSED |
| `pytest core/tests/test_smoke_navigation.py` | PASSED (o skipped con explicación si no hay BD) |
| `pytest` general + flag `-W error::DeprecationWarning` | 0 warnings de namespaces obsoletos |
| Apertura manual de `/usuarios/panel/` | 200 OK, sin NoReverseMatch |
| Clic en todos los enlaces del sidebar (admin) | Cada uno carga con 200 OK |

---

## Risks
| Riesgo | Mitigación |
|---|---|
| Las URLs sensibles a roles devuelvan 302/403 por falta de permisos en los tests | Usar `follow=True` y crear fixtures de `Usuario` con rol correcto para cada clase de test |
| Renombrar carpetas static rompa rutas sin usar `{% static %}` | Usar Grep antes y después del rename para asegurar que todas las referencias se actualizaron |
| El test de namespaces falle por URLs complejas que requieren kwargs no adivinables | Usar un `try_reverse_smart()` que pruebe args y kwargs habituales (`id`, `pk`, `codigo_*`, etc.) |
| El log anti-obsoleto en middleware genere ruido en desarrollo | Solo emita 1 log por namespace+usuario por sesión (cache en `request.session`) |
