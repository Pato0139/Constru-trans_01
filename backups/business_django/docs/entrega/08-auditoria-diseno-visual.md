# Fase 8 — Auditoría de diseño visual

## Criterios evaluados

| Criterio | Hallazgo inicial | Corrección aplicada |
|----------|------------------|---------------------|
| Contraste texto/fondo | `--color-accent` era azul `#1d5fa7` sobre negro, igual al secundario | `--color-accent: #f2a21b` (naranja) en `principal.css` |
| Texto secundario | `--color-muted` poco legible | Ajustado a `#e2e8f0` |
| Botones secundarios | `btn-outline-light` casi invisible | Clase global con borde dorado y hover |
| Jerarquía CTA | Botón principal vs cancelar | «Confirmar pedido» mantiene `btn-gold`; cancelar usa `btn-secondary-cta` |
| Mensajes de error | Alert rojo sobre oscuro | Mantener; validar en prueba si se leen |

## Archivos revisados

- `static/css/principal.css`
- `static/css/dashboard.css`
- `apps/clientes/templates/clientes/form.html`
- `templates/partials/sidebar.html`
- `apps/inventario/templates/inventario/lista.html` (botones `outline-light`)

## Checklist para la prueba con usuario (marcar en sesión)

- [ ] ¿Encuentra el botón «Solicitar pedido» en el menú cliente?
- [ ] ¿Lee los mensajes de error sin acercarse mucho a la pantalla?
- [ ] ¿Distingue campos obligatorios (ciudad, dirección)?
- [ ] ¿Confunde iconos del sidebar admin?
- [ ] ¿En móvil, el menú hamburguesa es visible?

## Mejoras pendientes (prioridad media)

1. Revisar `btn-outline-light` en listas de inventario (sustituir por `btn-secondary-cta`).
2. Aumentar tamaño de fuente en `form-text` de fechas (mín. 14px).
3. Probar contraste con herramienta WCAG (ratio ≥ 4.5:1 en textos normales).

## Redacción sugerida para el informe

«Se identificaron problemas de contraste por uso de acentos azules sobre fondo negro y botones outline de baja visibilidad. Se ajustó la variable `--color-accent` al color primario naranja y se reforzaron los estilos de botones secundarios para mejorar la detección de acciones no principales.»
