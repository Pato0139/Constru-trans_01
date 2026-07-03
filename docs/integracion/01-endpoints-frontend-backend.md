# Documentación de Endpoints Frontend-Backend

---

## Módulo Usuarios

| Módulo | Método | Ruta Real | Vista que la atiende | Autenticación | Tipo de Respuesta | Template Cliente |
|--------|--------|-----------|----------------------|---------------|------------------|------------------|
| Usuarios | GET/POST | `/usuarios/login/` | `login_usuario` | No | HTML | `usuarios/login.html` |
| Usuarios | GET/POST | `/usuarios/registro/` | `registro` | No | HTML | `usuarios/registro.html` |
| Usuarios | GET | `/usuarios/panel/` | `panel` | Sí | HTML | `usuarios/panel-admin.html` |
| Usuarios | GET | `/usuarios/logout/` | `cerrar_sesion` | Sí | Redirect | - |
| Usuarios | GET/POST | `/usuarios/perfil/editar/` | `editar_perfil` | Sí | HTML | `usuarios/editar_perfil.html` |
| Usuarios | GET | `/usuarios/conductores/` | `lista_conductores` | Sí (Admin) | HTML | `usuarios/conductores_lista.html` |
| Usuarios | POST | `/usuarios/conductores/asignar-vehiculo/<int:conductor_id>/` | `asignar_vehiculo_conductor` | Sí (Admin) | Redirect | - |
| Usuarios | GET | `/usuarios/panel-conductor/` | `panel_conductor` | Sí (Conductor) | HTML | `usuarios/panel-conductor.html` |
| Usuarios | GET | `/usuarios/mis-entregas/` | `mis_entregas` | Sí (Conductor) | HTML | `usuarios/mis-entregas.html` |
| Usuarios | GET | `/usuarios/recuperar/` | `CustomPasswordResetView` | No | HTML | `usuarios/recuperar_password.html` |

---

## Módulo Clientes

| Módulo | Método | Ruta Real | Vista que la atiende | Autenticación | Tipo de Respuesta | Template Cliente |
|--------|--------|-----------|----------------------|---------------|------------------|------------------|
| Clientes | GET | `/clientes/panel/` | `panel_cliente` | Sí (Cliente) | HTML | `clientes/lista.html` |
| Clientes | GET | `/clientes/mis-pedidos/` | `mis_pedidos` | Sí (Cliente) | HTML | `clientes/mis_pedidos.html` |
| Clientes | GET | `/clientes/mis-pagos/` | `mis_pagos` | Sí (Cliente) | HTML | `clientes/mis_pagos.html` |
| Clientes | GET | `/clientes/seguimiento/` | `seguimiento_pedidos` | Sí (Cliente) | HTML | `clientes/seguimiento.html` |
| Clientes | GET/POST | `/clientes/pedido/crear/` | `crear_pedido` | Sí (Cliente) | HTML | `clientes/form.html` |

---

## Módulo Inventario

| Módulo | Método | Ruta Real | Vista que la atiende | Autenticación | Tipo de Respuesta | Template Cliente |
|--------|--------|-----------|----------------------|---------------|------------------|------------------|
| Inventario | GET | `/inventario/materiales/` | `materiales_lista` | Sí (Admin/Empleado) | HTML | `inventario/lista.html` |
| Inventario | GET/POST | `/inventario/materiales/crear/` | `crear_material` | Sí (Admin) | HTML | `inventario/form.html` |
| Inventario | GET | `/inventario/stock/` | `stock_lista` | Sí (Admin/Empleado) | HTML | `inventario/stock.html` |
| Inventario | GET | `/inventario/movimientos/` | `movimientos_lista` | Sí (Admin/Empleado) | HTML | `inventario/movimientos.html` |
| Inventario | GET | `/inventario/api/materiales/` | `api_materiales` | Sí | JSON | - |

---

## Módulo Órdenes

| Módulo | Método | Ruta Real | Vista que la atiende | Autenticación | Tipo de Respuesta | Template Cliente |
|--------|--------|-----------|----------------------|---------------|------------------|------------------|
| Órdenes | GET | `/ordenes/lista/` | `lista_pedidos_admin` | Sí (Admin) | HTML | `ordenes/lista_ordenes.html` |
| Órdenes | GET/POST | `/ordenes/entregas/crear/<int:orden_id>/` | `crear_entrega` | Sí (Admin) | HTML | `ordenes/asignar_entrega.html` |
| Órdenes | GET | `/ordenes/detalle/<int:id>/` | `ver_pedido_admin` | Sí (Admin) | HTML | `ordenes/detalle.html` |

---

## Módulo IA

| Módulo | Método | Ruta Real | Vista que la atiende | Autenticación | Tipo de Respuesta | Template Cliente |
|--------|--------|-----------|----------------------|---------------|------------------|------------------|
| IA | POST | `/ia/chat/` | `chat_ia` | Sí | JSON | - |
| IA | POST | `/ia/feedback/` | `feedback_ia` | Sí | JSON | - |

---

## Notas Importantes
- Todas las vistas HTML requieren autenticación excepto login, registro y recuperación de contraseña
- El endpoint `/ia/chat/` solo acepta POST y devuelve JSON
- La API de materiales (`/inventario/api/materiales/`) devuelve una lista de materiales con su stock y precio
