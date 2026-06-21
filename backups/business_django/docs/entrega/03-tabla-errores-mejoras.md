# Tabla de errores y mejoras — Constru-Trans

**Leyenda de tipos:** Funcional | Usabilidad | Visual | Validación  
**Prioridad:** Alta | Media | Baja

> Las filas marcadas como **(código / revisión estática)** provienen del análisis del repositorio. Las filas de **(prueba con usuario)** debes completarlas tras la sesión con tu compañero externo.

---

## Hallazgos consolidados

| N.º | Rol | Tarea | Tipo | Descripción | Evidencia | Impacto | Solución propuesta | Prioridad |
|-----|-----|-------|------|-------------|-----------|---------|-------------------|-----------|
| 1 | Cliente | Solicitar pedido | Validación / Usabilidad | ~~No había selector de ciudades~~ **Corregido:** selector + validación en `core/despacho.py` | `form.html` + `clientes/views.py` | Evita destinos fuera de zona | Mantener lista de ciudades actualizada en `CIUDADES_DESPACHO` | Resuelto |
| 2 | Cliente | Solicitar pedido | Funcional | Redondeo en acumulación JS del total | `form.html` — suma sin redondear | Posible diferencia de centavos | **Corregido:** `Math.round(x*100)/100` al sumar/restar | Resuelto |
| 3 | Cliente | Solicitar pedido | Funcional | Al agregar el mismo material dos veces, el total en UI suma líneas; en servidor cada línea descuenta stock por separado (comportamiento correcto pero no obvio) | JS `agregarMaterial()` acumula sin fusionar líneas | Confusión si el usuario espera una sola fila por material | Fusionar líneas duplicadas en UI o avisar «material ya agregado» | Baja |
| 4 | Cliente | Consultar pedidos | Visual | Botón secundario «Cancelar y Volver» usa `btn-outline-light` sobre fondo oscuro | `form.html` línea 130 | Bajo contraste, difícil de localizar | Aumentar contraste (borde/accent), tamaño mínimo 44px | Media |
| 5 | Admin / Global | Navegación | Visual | Acento azul igual al secundario sobre fondo negro | `principal.css` | Baja visibilidad de CTAs | **Corregido:** `--color-accent: #f2a21b`, muted más claro, botones outline visibles | Resuelto |
| 6 | Admin | Panel lateral | Usabilidad | Menú admin con secciones colapsables (Ventas, Inventario, etc.) requiere varios clics para tareas frecuentes | `templates/partials/sidebar.html` | Usuarios nuevos se pierden al asignar pedido | Acceso directo «Pedidos» y «Nueva entrega» en primer nivel | Media |
| 7 | Repositorio | — | Proceso | Migraciones Django y backups JSON estaban versionados pese a indicación del instructor | `git ls-files` previo a corrección | Repositorio pesado, conflictos en equipo | `.gitignore` actualizado; `git rm --cached`; generar migraciones local con `makemigrations` | Alta |
| 8 | Cliente | Fecha de entrega | Validación | Formato de fecha exige DD/MM/YYYY HH:MM; mensaje de error solo tras enviar | `parse_fecha_entrega` en `clientes/views.py` | Abandono o reintentos | Placeholder + validación en cliente + date picker | Media |
| 9 | Cliente | Solicitar pedido | Funcional | Stock insuficiente muestra error genérico tras enviar formulario completo | `crear_pedido` líneas 256-260 | Frustración, pérdida de datos ingresados | Validar stock al agregar material en JS o al seleccionar cantidad | Media |
| 10 | Admin | Asignar entrega | Usabilidad | Flujo repartido entre lista de pedidos, detalle y URL `entregas/crear/` | `ordenes/urls.py` | Participante no encuentra «asignar transporte» | Botón explícito «Asignar conductor/vehículo» en detalle del pedido | Alta |
| 11 | _[prueba]_ | _[tarea]_ | _[tipo]_ | _[descripción observada]_ | _[captura / tiempo]_ | _[impacto]_ | _[acción concreta]_ | _[Alta/Media/Baja]_ |
| 12 | _[prueba]_ | _[tarea]_ | _[tipo]_ | | | | | |

---

## Tabla de cálculos (completar en prueba)

| Caso | Cantidad | Precio unitario | Cálculo esperado | Cálculo mostrado | Resultado | Acción técnica si falla |
|------|----------|-----------------|------------------|------------------|-----------|-------------------------|
| 1 | 3 | 2850 | 8550 | _[llenar]_ | | Revisar `precio_unitario * cantidad` en modelo y vista |
| 2 | 5 | 1000 | 5000 | | | |
| 3 | 2 | 3499 | 6998 | | | Evitar redondeo prematuro en JS |

---

## Mejoras priorizadas (resumen ejecutivo)

1. Selector de ciudades de despacho con regla de negocio documentada (Opción B: varias ciudades).
2. Corregir paleta de contraste (acento vs. fondo oscuro).
3. Simplificar flujo admin: pedido → asignar entrega.
4. Alinear total visual y total en base de datos.
5. Mantener repositorio sin migraciones ni backups sensibles.
