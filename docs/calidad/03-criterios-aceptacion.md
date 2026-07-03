# Criterios de Aceptación por Componente

---

## Componente: Autenticación y Usuarios
| ID | Criterio | Verificación |
|----|----------|--------------|
| CA-AUTH-001 | El usuario puede registrarse con nombres, apellidos, correo, documento y contraseña | `usuarios/views.py`, `usuarios/forms.py` |
| CA-AUTH-002 | El formulario de registro valida que el correo y documento sean únicos | `RegistroForm.clean_correo()`, `RegistroForm.clean_documento()` |
| CA-AUTH-003 | El login exige confirmación del campo captcha y muestra error si falta | `LoginForm` en `usuarios/forms.py` |
| CA-AUTH-004 | El usuario puede recuperar su contraseña mediante un enlace por correo | `usuarios/urls.py`, `usuarios/forms.py` |
| CA-AUTH-005 | El usuario puede editar su perfil y foto de perfil | `usuarios/views.py`, `usuarios/templates/usuarios/editar_perfil.html` |

---

## Componente: Inventario
| ID | Criterio | Verificación |
|----|----------|--------------|
| CA-INV-001 | El admin puede crear, editar y eliminar materiales de construcción | `inventario/views.py`, `inventario/templates/inventario/` |
| CA-INV-002 | El stock se actualiza en entradas/salidas mediante lógica de vistas y servicio Kardex | `inventario/services/kardex.py`, `clientes/views.py`, `gestion_pedidos/views.py` |
| CA-INV-003 | El admin puede ver el historial de movimientos de inventario | `inventario/views.py`, `MovimientoInventario` model |

---

## Componente: Pedidos y Órdenes
| ID | Criterio | Verificación |
|----|----------|--------------|
| CA-PED-001 | El cliente puede crear un pedido con múltiples items | `gestion_pedidos/views.py`, `Pedido` model, `DetallePedido` model |
| CA-PED-002 | El total del pedido se calcula automáticamente al guardar un detalle | `DetallePedido.save()`, `Pedido.calcular_total()` |
| CA-PED-003 | El admin puede asignar una entrega a un pedido con conductor y vehículo | `ordenes/views.py`, `Entrega` model |
| CA-PED-004 | El conductor puede ver la lista de entregas asignadas | `usuarios/views.py`, `usuarios/templates/usuarios/mis-entregas.html` |

---

## Componente: Facturación y Pagos
| ID | Criterio | Verificación |
|----|----------|--------------|
| CA-FAC-001 | El sistema permite crear facturas asociadas a pedidos | `facturacion/models.py`, `facturacion/views.py` |
| CA-FAC-002 | El total pagado de una factura se calcula como la suma de sus pagos | `Factura.total_pagado` (property) |
| CA-FAC-003 | El estado de la factura se actualiza a "pagada" si el total pagado es mayor o igual al total | `Pago` model en `pagos/models.py` (signal allí) |
| CA-FAC-004 | El cliente puede ver el historial de sus pagos | `clientes/views.py`, `clientes/templates/clientes/mis_pagos.html` |

---

## Componente: Asistente IA
| ID | Criterio | Verificación |
|----|----------|--------------|
| CA-IA-001 | El usuario autenticado puede enviar preguntas al asistente IA | `ia/views.py`, `ia/urls.py` |
| CA-IA-002 | El sistema devuelve una respuesta JSON al chat | `ia/views.py` |

---

## Notas Importantes
- No hay signal automática para generar factura al crear pedido (esto debe hacerse manualmente o implementarse)
- El stock no se actualiza automáticamente al crear un pedido (debe manejarse manualmente o con un signal)
