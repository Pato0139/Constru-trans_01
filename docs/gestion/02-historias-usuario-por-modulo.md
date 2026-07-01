# Historias de Usuario por Módulo

---

## Módulo Usuarios

| ID | Historia de Usuario | Criterios de Aceptación | Evidencia |
|----|---------------------|-------------------------|-----------|
| USU-001 | Como usuario quiero registrarme para acceder al sistema | - Formulario de registro con nombres, apellidos, email, documento, contraseña<br>- Validación de correo duplicado en formulario<br>- Redirección al login después de registro | `usuarios/views.py`, `usuarios/forms.py`, `usuarios/templates/usuarios/registro.html` |
| USU-002 | Como usuario quiero iniciar sesión para usar las funcionalidades | - Login con username/email y contraseña<br>- Mensajes de error por credenciales incorrectas<br>- Redirección al panel según rol | `usuarios/views.py`, `usuarios/templates/usuarios/login.html` |
| USU-003 | Como usuario quiero editar mi perfil para actualizar mis datos | - Formulario de edición con campos personalizables<br>- Subida de foto de perfil<br>- Guardado inmediato de cambios | `usuarios/views.py`, `usuarios/forms.py`, `usuarios/templates/usuarios/editar_perfil.html` |
| USU-004 | Como usuario quiero recuperar mi contraseña si la olvido | - Formulario de solicitud de recuperación por email<br>- Enlace de restablecimiento válido por tiempo limitado<br>- Formulario para ingresar nueva contraseña | `usuarios/urls.py`, `usuarios/templates/usuarios/recuperar_password.html` |
| USU-005 | Como admin quiero gestionar conductores para asignar vehículos | - Lista de conductores con estado y vehículo actual<br>- Formulario para asignar/desasignar vehículos<br>- Historial de asignaciones | `usuarios/views.py`, `usuarios/templates/usuarios/conductores_lista.html` |

---

## Módulo Clientes

| ID | Historia de Usuario | Criterios de Aceptación | Evidencia |
|----|---------------------|-------------------------|-----------|
| CLI-001 | Como cliente quiero ver mi panel principal para acceder a mis opciones | - Vista de panel con enlaces a mis pedidos, seguimiento y pagos<br>- Información básica del perfil del cliente | `clientes/views.py`, `clientes/templates/clientes/base_cliente.html` |
| CLI-002 | Como cliente quiero consultar el seguimiento de mis pedidos para conocer su estado | - Lista de mis pedidos con estado, fecha y dirección<br>- Detalle completo del pedido con items y entrega (si aplica) | `clientes/views.py`, `clientes/templates/clientes/seguimiento.html` |
| CLI-003 | Como cliente quiero ver mis pagos para revisar mi historial financiero | - Historial de pagos asociados a mis facturas<br>- Información de método y fecha de cada pago | `clientes/views.py`, `clientes/templates/clientes/mis_pedidos.html` |

---

## Módulo Inventario

| ID | Historia de Usuario | Criterios de Aceptación | Evidencia |
|----|---------------------|-------------------------|-----------|
| INV-001 | Como admin quiero registrar materiales para el catálogo | - Formulario con nombre, unidad, precio y descripción<br>- Relación con unidad de medida estándar<br>- Listado de materiales creados | `inventario/views.py`, `inventario/templates/inventario/form.html` |
| INV-002 | Como admin quiero ver el stock para controlar inventario | - Vista de stock por material con cantidad actual y mínimo<br>- Ubicación del material (si aplica) | `inventario/views.py`, `inventario/templates/inventario/stock.html` |
| INV-003 | Como admin quiero registrar movimientos de inventario para auditoría | - Tipo de movimiento (entrada/salida)<br>- Cantidad y material involucrado<br>- Usuario que realiza la acción y fecha | `inventario/models.py`, `inventario/templates/inventario/movimientos.html` |

---

## Módulo Compras

| ID | Historia de Usuario | Criterios de Aceptación | Evidencia |
|----|---------------------|-------------------------|-----------|
| COM-001 | Como admin quiero registrar proveedores para comprar | - Formulario con nombre de empresa, NIT, teléfono y correo<br>- Validación de NIT único<br>- Lista de proveedores | `compras/views.py`, `compras/templates/compras/proveedores_lista.html` |
| COM-002 | Como admin quiero registrar compras para reponer stock | - Formulario para seleccionar proveedor y añadir items<br>- Cálculo automático del total de la compra<br>- Relación con detalle de compra | `compras/views.py`, `compras/models.py`, `compras/signals.py` |

---

## Módulo Pedidos y Órdenes

| ID | Historia de Usuario | Criterios de Aceptación | Evidencia |
|----|---------------------|-------------------------|-----------|
| PED-001 | Como cliente quiero crear pedidos para solicitar materiales | - Formulario para seleccionar materiales y cantidades<br>- Cálculo automático del total del pedido<br>- Estado inicial "pendiente" | `gestion_pedidos/views.py`, `gestion_pedidos/templates/gestion_pedidos/crear_pedido.html` |
| PED-002 | Como admin quiero asignar entregas para cumplir pedidos | - Formulario para asignar conductor y vehículo a un pedido<br>- Estado de entrega actualizable<br>- Relación uno-a-muchos entre pedido y entregas | `ordenes/views.py`, `ordenes/templates/ordenes/asignar_entrega.html` |
| PED-003 | Como conductor quiero ver mis entregas para cumplirlas | - Lista de entregas asignadas al conductor autenticado<br>- Estado y detalles de cada entrega | `usuarios/views.py`, `usuarios/templates/usuarios/mis-entregas.html` |

---

## Módulo Facturación y Pagos

| ID | Historia de Usuario | Criterios de Aceptación | Evidencia |
|----|---------------------|-------------------------|-----------|
| FAC-001 | Como admin quiero gestionar facturas para los pedidos | - Lista de facturas asociadas a pedidos<br>- Campos para subtotal, IVA y total<br>- Estado de factura (pendiente/pagada/anulada) | `facturacion/views.py`, `facturacion/models.py`, `facturacion/templates/facturacion/lista.html` |
| FAC-002 | Como cliente/admin quiero ver el saldo pendiente de una factura | - Total pagado calculado como suma de pagos asociados<br>- Saldo pendiente = total - total pagado<br>- Estado de factura actualizado a "pagada" si saldo <= 0 | `facturacion/models.py`, `pagos/models.py`, `pagos/signals.py` |
| FAC-003 | Como admin quiero registrar pagos para facturas | - Formulario para seleccionar factura, método y monto<br>- Signal que actualiza estado de factura después de pago<br>- Historial de pagos | `pagos/views.py`, `pagos/models.py`, `pagos/signals.py` |

---

## Módulo IA

| ID | Historia de Usuario | Criterios de Aceptación | Evidencia |
|----|---------------------|-------------------------|-----------|
| IA-001 | Como usuario quiero consultar al asistente IA para ayuda | - Interfaz de chat para enviar preguntas<br>- Respuestas contextualizadas del asistente<br>- Historial de conversación | `ia/views.py`, `ia/templates/ia/chat.html`, `ia/services/llm_service.py` |
