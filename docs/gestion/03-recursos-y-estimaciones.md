# Recursos Técnicos y Estimaciones

## Recursos Asignados

| Rol | Persona | Horas/Sprint |
|-----|---------|--------------|
| Desarrollador Full Stack | Edward | 50 |
| Evaluador/Profesor | - | - |

---

## Estimación de Esfuerzo Total

| Sprint | Horas Estimadas | Estado |
|--------|-----------------|--------|
| Sprint 1: Usuarios y Autenticación | 44 | ✅ Completado |
| Sprint 2: Inventario y Compras | 45 | ✅ Completado |
| Sprint 3: Pedidos y Transporte | 36 | ✅ Completado |
| Sprint 4: Facturación, Reportes e IA | 47 | ✅ Completado |
| **Total** | **172** | - |

---

## Estimación Detallada por Componente

| Componente | Responsable | Horas Estimadas | Dependencia | Recursos Técnicos | Entregable |
|------------|-------------|-----------------|-------------|--------------------|------------|
| Usuarios y Autenticación | Edward | 20 | - | Django Auth, Forms, Templates | Registro, login, perfil, recuperación de contraseña, gestión de conductores |
| Clientes | Edward | 12 | Usuarios | Vistas cliente, Templates | Panel, seguimiento, pagos |
| Inventario | Edward | 25 | Usuarios | ORM, Templates, Kardex | CRUD materiales, stock, movimientos, unidades de inventario |
| Compras | Edward | 18 | Inventario | Compra, detalle, proveedor | Flujo de compras |
| Gestión de Pedidos | Edward | 18 | Inventario | SolicitudPedido, detalle | Pedido cliente |
| Órdenes y Transporte | Edward | 22 | Pedidos | Relaciones, Vistas Admin | Entregas, asignación conductor-vehículo |
| Facturación y Pagos | Edward | 18 | Pedidos | ORM, Lógica de saldos | Flujo financiero |
| Reportes | Edward | 12 | Facturación | ReportLab, openpyxl | Exportación de reportes PDF y Excel |
| IA | Edward | 15 | Usuarios | OpenAI API | Chat asistente IA |
| Documentación y Pruebas | Edward | 20 | Todos | Markdown, pytest, CI | Evidencia académica |

---

## Desglose por componente del plan de construcción

| Componente | Responsable | Horas | Dependencia | Recurso técnico principal | Entregable |
|------------|-------------|-------|-------------|---------------------------|------------|
| Usuarios | Edward | 20 | - | Django Auth, forms, templates | Registro, login, perfil |
| Clientes | Edward | 12 | Usuarios | Vistas cliente, templates | Panel, seguimiento, pagos |
| Inventario | Edward | 25 | Usuarios | ORM, stock, Kardex | Materiales, stock, movimientos |
| Compras | Edward | 18 | Inventario | Compra, detalle, proveedor | Flujo de compras |
| Gestión de pedidos | Edward | 18 | Inventario | SolicitudPedido, detalle | Pedido cliente |
| Órdenes y transporte | Edward | 22 | Pedidos | Pedido, Entrega, Vehículo | Asignación y entrega |
| Facturación y pagos | Edward | 18 | Órdenes | Factura, Pago | Flujo financiero |
| Reportes | Edward | 12 | Facturación | ReportLab, openpyxl | Exportes PDF/Excel/XML |
| IA | Edward | 15 | Usuarios | OpenAI, servicios IA | Chat contextual |
| Documentación y pruebas | Edward | 20 | Todos | Markdown, pytest, CI | Evidencia académica |

---

## Matriz de Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Fallo en conexión a BD remota | Alta | Alto | Arquitectura híbrida con SQLite local |
| Errores en pruebas | Media | Medio | Pruebas unitarias por módulo |
| Retrasos en documentación | Media | Medio | Documentación en paralelo al desarrollo |

---

## Dependencias Externas

| Dependencia | Versión | Propósito | Módulo |
|-------------|---------|-----------|--------|
| Django | 5.1.5 | Framework web | Todos |
| PostgreSQL | 16 | BD remota | Usuarios, Clientes, Historial, etc. |
| OpenAI API | 1.51.2 | Asistente IA | ia |
| ReportLab | 4.4.10 | Generar PDFs | reportes |
| openpyxl | 3.1.5 | Excel | reportes |
| django-environ | 0.11.2 | Variables de entorno | core |
