# Fase 9 — Protocolo de prueba de usabilidad (Administrador)

Misma regla que cliente: **no explicar** dónde hacer clic. Solo dar la tarea.

## Preparación

- Usuario admin de prueba (credenciales del `seed` o creado en setup).
- Sistema en ejecución: `python manage.py runserver`
- Plantilla: [02-plantilla-prueba-usabilidad.md](02-plantilla-prueba-usabilidad.md)
- Cronómetro y carpeta `evidencia/`

## Guion inicial

> «Vas a usar el panel de administración para completar varias tareas. No te voy a guiar; hazlo como creas que debería funcionar un sistema de este tipo.»

## Tareas mínimas (instrucciones al participante)

| N.º | Instrucción literal al participante | Ruta esperada (solo para el observador) |
|-----|-------------------------------------|----------------------------------------|
| A1 | «Inicia sesión como administrador.» | `/usuarios/login/` |
| A2 | «Registra un material nuevo en el inventario.» | Inventario → Materiales → Crear |
| A3 | «Consulta la lista de pedidos de clientes.» | Ventas → Pedidos |
| A4 | «Abre un pedido pendiente y asígnale un conductor.» | Detalle → «Asignar Conductor» |
| A5 | «Registra un vehículo en la flota.» | Inventario y Flota → Vehículos |
| A6 | «Consulta un reporte y expórtalo si puedes.» | Reportes → Exportar |
| A7 | «Cambia el estado de un pedido a entregado.» | Detalle pedido → Control Maestro |

## Qué observar (Fase 4 aplicada a admin)

1. ¿Encuentra el menú lateral colapsable (Ventas, Inventario)?
2. ¿Localiza «Pedidos» sin ayuda?
3. ¿Entiende «Asignar Conductor» vs «Modificar»?
4. ¿Los formularios de material/vehículo tienen etiquetas claras?
5. ¿Errores de validación son comprensibles?
6. Tiempo por tarea y si pide ayuda.

## Tabla de registro (copiar y completar)

| N.º | Tarea | ¿Completó? | Tiempo | Observación | Tipo error | Mejora |
|-----|-------|------------|--------|-------------|------------|--------|
| A1 | Login admin | | | | | |
| A2 | Crear material | | | | | |
| A3 | Lista pedidos | | | | | |
| A4 | Asignar conductor | | | | | |
| A5 | Registrar vehículo | | | | | |
| A6 | Reportes | | | | | |
| A7 | Cambiar estado | | | | | |

## Preguntas finales (3 min)

1. ¿Qué fue lo más confuso del panel de administración?
2. ¿Qué fue lo más fácil?
3. ¿Qué reorganizarías del menú?

## Evidencia

- Captura del panel tras login: `evidencia/admin-A1-panel.png`
- Captura de asignación de conductor: `evidencia/admin-A4-asignar.png`
