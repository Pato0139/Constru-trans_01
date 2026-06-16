# Plantilla — Prueba de usabilidad Constru-Trans

## Datos de la sesión

| Campo | Valor |
|--------|--------|
| Fecha | _[completar]_ |
| Facilitador (observador) | _[nombre]_ |
| Participante (externo al proyecto) | _[nombre o código P1]_ |
| Rol probado | Cliente / Administrador |
| Entorno | URL local / servidor / navegador |
| Duración total | _[minutos]_ |
| Grabación (sí/no) | _[enlace o carpeta evidencia/]_ |

## Consentimiento y guion inicial (leer al participante)

> Voy a pedirte que uses este sistema para hacer unas tareas. No te voy a explicar cómo funciona, porque necesito observar si la interfaz se entiende sola. Hazlo como tú creas correcto. Si algo no está claro, intenta resolverlo como lo harías en cualquier aplicación.

**Si pregunta dónde hacer clic:** «Hazlo como te parezca más lógico.»

---

## Registro por tarea

| N.º | Rol | Tarea asignada (solo instrucción dada) | ¿Completó? | Tiempo | Entendió de inmediato | Primer clic / acción | Duda o confusión | Error funcional | Comentario espontáneo | Mejora propuesta |
|-----|-----|----------------------------------------|------------|--------|------------------------|----------------------|------------------|-----------------|----------------------|------------------|
| 1 | Cliente | «Inicia sesión como cliente.» | Sí / No | | | | | | | |
| 2 | Cliente | «Solicita un pedido con al menos dos materiales.» | | | | | | | | |
| 3 | Cliente | «Consulta el estado de un pedido.» | | | | | | | | |
| 4 | Cliente | «Modifica un pedido pendiente.» | | | | | | | | |
| 5 | Admin | «Inicia sesión como administrador.» | | | | | | | | |
| 6 | Admin | «Crea un material nuevo en inventario.» | | | | | | | | |
| 7 | Admin | «Consulta la lista de pedidos y abre uno.» | | | | | | | | |
| 8 | Admin | «Asigna transporte o registra una entrega.» | | | | | | | | |

---

## Prueba de cálculos (completar durante tarea «Solicitar pedido»)

| Caso | Cantidad | Precio unitario (catálogo) | Cálculo esperado | Total mostrado en pantalla | Total guardado en BD | Resultado |
|------|----------|----------------------------|------------------|----------------------------|----------------------|-----------|
| A | 3 | 2850 | 8550 | | | Correcto / Incorrecto |
| B | 5 | 1000 | 5000 | | | |
| C | 2 | 3499 | 6998 | | | |

**Notas técnicas si hay error:** revisar `DetallePedido.subtotal`, `Pedido.calcular_total()`, JavaScript `formatCurrency()` en `clientes/form.html`.

---

## Prueba de destinos / ciudades

| Pregunta | Observación |
|----------|-------------|
| ¿El usuario supo dónde puede despachar? | |
| ¿Usó campo de texto libre o selector? | |
| ¿Hubo errores de escritura en dirección? | |

---

## Preguntas finales al participante (3 minutos)

1. ¿Qué fue lo más confuso?
2. ¿Qué fue lo más fácil?
3. ¿Qué mejorarías de la interfaz?

**Respuestas:**

- Confuso: _
- Fácil: _
- Mejoraría: _

---

## Evidencia adjunta (checklist)

- [ ] Capturas de pantalla por tarea (`docs/entrega/evidencia/`)
- [ ] Video o grabación de pantalla (opcional)
- [ ] Segunda sesión con otro participante (recomendado)
