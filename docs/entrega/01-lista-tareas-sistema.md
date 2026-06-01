# Lista de tareas del sistema Constru-Trans

Inventario de acciones desde la perspectiva del usuario (no técnica). Rutas de referencia entre paréntesis.

---

## Rol: Cliente

| # | Tarea | Descripción breve | Ruta / módulo |
|---|--------|-------------------|---------------|
| 1 | Registrarse en el sistema | Crear cuenta como cliente nuevo | `/usuarios/registro/` |
| 2 | Iniciar sesión | Acceder con correo y contraseña | `/usuarios/login/` |
| 3 | Recuperar contraseña | Solicitar enlace de restablecimiento por correo | `/usuarios/recuperar/` |
| 4 | Ver panel principal (dashboard) | Resumen de pedidos activos, entregas y gasto | `/clientes/panel/` |
| 5 | Consultar catálogo de materiales | Ver materiales disponibles al crear pedido | `/clientes/pedido/crear/` |
| 6 | Solicitar un pedido | Agregar materiales, dirección y fecha de entrega | `/clientes/pedido/crear/` |
| 7 | Ver total estimado antes de confirmar | Revisar suma de líneas en formulario de pedido | Formulario de pedido (JS) |
| 8 | Consultar mis pedidos | Listar pedidos propios con estado | `/clientes/mis-pedidos/` |
| 9 | Modificar un pedido pendiente | Editar materiales o dirección si estado = pendiente | `/clientes/pedido/editar/<id>/` |
| 10 | Cancelar un pedido | Cancelar pedido en estado permitido | `/clientes/orden/cancelar/<id>/` |
| 11 | Seguimiento de pedidos | Ver estado en ruta / pendiente / entregado | `/clientes/seguimiento/` |
| 12 | Consultar historial de entregas | Ver pedidos ya entregados | `/clientes/historial/` |
| 13 | Editar perfil de cliente | Actualizar datos personales y dirección principal | `/clientes/perfil/` |
| 14 | Consultar mis facturas | Ver facturas asociadas (si aplica) | `/facturacion/mis-facturas/` |
| 15 | Cerrar sesión | Salir del sistema de forma segura | `/usuarios/logout/` |

---

## Rol: Administrador

| # | Tarea | Descripción breve | Ruta / módulo |
|---|--------|-------------------|---------------|
| 1 | Iniciar sesión como administrador | Acceso al panel de control | `/usuarios/login/` |
| 2 | Ver panel general | Dashboard con indicadores del negocio | `/usuarios/panel/` |
| 3 | Gestionar usuarios del sistema | Listar, crear, editar, activar/desactivar usuarios | `/usuarios/usuarios/` |
| 4 | Gestionar clientes (vía usuarios) | Administrar cuentas con rol cliente | Módulo usuarios |
| 5 | Gestionar conductores | Listar y administrar conductores | `/usuarios/conductores/` |
| 6 | Crear material de construcción | Registrar nuevo material en inventario | `/inventario/materiales/crear/` |
| 7 | Editar material | Modificar nombre, precio, tipo, etc. | `/inventario/materiales/editar/<id>/` |
| 8 | Eliminar material | Dar de baja material del catálogo | `/inventario/materiales/eliminar/<id>/` |
| 9 | Gestionar tipos de material | Catálogo de categorías/tipos | `/inventario/tipos/` |
| 10 | Consultar y ajustar stock | Ver niveles y editar cantidades | `/inventario/stock/` |
| 11 | Registrar entrada de inventario | Aumentar stock por compra/entrada | `/inventario/entrada/` |
| 12 | Consultar movimientos de inventario | Historial de entradas/salidas | `/inventario/movimientos/` |
| 13 | Gestionar proveedores | CRUD de proveedores | `/compras/proveedores/` |
| 14 | Registrar compras a proveedores | Crear y editar órdenes de compra | `/compras/crear/` |
| 15 | Cambiar estado de compras | Aprobar, recibir o cancelar compras | `/compras/estado/<id>/` |
| 16 | Consultar pedidos de clientes | Lista global de pedidos | `/ordenes/lista/` |
| 17 | Ver detalle de un pedido | Materiales, totales, cliente, dirección | `/ordenes/detalle/<id>/` |
| 18 | Agregar materiales a pedido (admin) | Ampliar líneas de un pedido existente | `/ordenes/agregar-materiales/<id>/` |
| 19 | Asignar transporte / crear entrega | Vincular conductor, vehículo y ruta | `/ordenes/entregas/crear/<orden_id>/` |
| 20 | Gestionar entregas | Listar y actualizar entregas en curso | `/ordenes/entregas/` |
| 21 | Actualizar estado de pedidos | Cambiar pendiente / en ruta / entregado | Detalle de pedido / entregas |
| 22 | Descargar factura PDF de pedido | Generar documento del pedido | `/ordenes/factura/<id>/` |
| 23 | Gestionar facturación | Listar, anular o ajustar montos de facturas | `/facturacion/` |
| 24 | Consultar historial de pagos | Ver pagos registrados | `/pagos/historial/` |
| 25 | Gestionar vehículos | CRUD de flota | `/transporte/vehiculos/` |
| 26 | Desactivar o eliminar vehículo | Baja lógica de unidades | `/transporte/vehiculos/desactivar/<id>/` |
| 27 | Consultar reportes | Panel de reportes administrativos | `/reportes/admin/` |
| 28 | Exportar reportes (PDF/Excel/XML) | Descargar informes | `/reportes/exportar/...` |
| 29 | Consultar historial de actividad | Auditoría de acciones en el sistema | `/historial/` |
| 30 | Gestionar licencias del sistema | Módulo de licenciamiento | `/licensing/` |
| 31 | Editar perfil de administrador | Datos del usuario admin | `/usuarios/perfil/admin/` |
| 32 | Ver notificaciones | Alertas del sistema | `/usuarios/notificaciones/` |
| 33 | Cerrar sesión | Salir del panel admin | `/usuarios/logout/` |

---

## Rol adicional: Conductor (referencia para pruebas ampliadas)

| # | Tarea | Ruta |
|---|--------|------|
| 1 | Ver panel del conductor | `/usuarios/panel-conductor/` |
| 2 | Consultar pedidos asignados | `/usuarios/pedidos-conductor/` |
| 3 | Ver mis entregas realizadas | `/usuarios/mis-entregas/` |
| 4 | Editar perfil de conductor | `/usuarios/perfil-conductor/` |

---

## Tareas sugeridas para prueba de usabilidad (mínimo recomendado)

**Cliente:** 2, 6, 8, 9, 11, 13  
**Administrador:** 1, 6, 16, 19, 25, 27
