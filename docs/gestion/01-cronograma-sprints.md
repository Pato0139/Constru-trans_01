# Cronograma de Sprints

## Sprint 1: Usuarios, Clientes y Autenticación

| Módulo | Historia de Usuario | Tareas Técnicas | Responsable | Horas | Dependencia | Criterio de Aceptación | Evidencia |
|--------|---------------------|-----------------|-------------|-------|-------------|------------------------|-----------|
| Usuarios | Como usuario quiero registrarme para acceder al sistema | Crear modelo Usuario, crear formulario, implementar vista de registro | Edward | 12 | - | El usuario puede crear cuenta con email y contraseña validos | usuarios/views.py |
| Usuarios | Como usuario quiero iniciar sesión para usar las funcionalidades | Implementar login con Django Auth, configurar seguridad | Edward | 8 | Registro de usuario | El usuario puede iniciar sesión con credenciales válidas | core/settings/base.py |
| Usuarios | Como usuario quiero editar mi perfil para actualizar mis datos | Crear vista de edición, formulario, manejo de foto | Edward | 10 | Login | El usuario puede cambiar sus datos y foto de perfil | usuarios/templates/editar_perfil.html |
| Clientes | Como cliente quiero tener perfil para ver mis pedidos | Crear modelo Cliente, relacionar con Usuario | Edward | 8 | Registro de usuario | El cliente tiene su perfil empresarial | clientes/models.py |
| Inicio | Como usuario quiero ver la página principal para navegar | Crear template home, menú de navegación | Edward | 6 | Login | El usuario accede al dashboard según su rol | inicio/templates/home.html |

**Entregable Sprint 1:** Sistema de autenticación completo, perfiles de usuario y página de inicio.

---

## Sprint 2: Inventario y Compras

| Módulo | Historia de Usuario | Tareas Técnicas | Responsable | Horas | Dependencia | Criterio de Aceptación | Evidencia |
|--------|---------------------|-----------------|-------------|-------|-------------|------------------------|-----------|
| Inventario | Como admin quiero registrar materiales para el catálogo | Modelos Material, UnidadMedida, Stock, CRUD | Edward | 15 | Sprint 1 | El admin agrega materiales con su unidad y stock | inventario/models.py |
| Inventario | Como admin quiero ver el stock para controlar inventario | Vista de stock, alerts de stock mínimo | Edward | 10 | Registro de materiales | El sistema muestra stock actual y alertas | inventario/templates/inventario/stock.html |
| Compras | Como admin quiero registrar proveedores para comprar | Modelo Proveedor, CRUD proveedores | Edward | 8 | Sprint 1 | El admin agrega y edita proveedores | compras/models.py |
| Compras | Como admin quiero registrar compras para reponer stock | Modelos Compra, DetalleCompra, actualizar stock | Edward | 12 | Proveedores + Materiales | El admin registra compra y se actualiza stock automáticamente | compras/views.py |

**Entregable Sprint 2:** Catálogo completo, manejo de stock, proveedores y compras.

---

## Sprint 3: Pedidos, Órdenes y Transporte

| Módulo | Historia de Usuario | Tareas Técnicas | Responsable | Horas | Dependencia | Criterio de Aceptación | Evidencia |
|--------|---------------------|-----------------|-------------|-------|-------------|------------------------|-----------|
| Pedidos | Como cliente quiero crear pedidos para solicitar materiales | Modelo Pedido, DetallePedido, formulario | Edward | 14 | Sprint 2 | El cliente crea pedido seleccionando materiales y cantidades | gestion_pedidos/models.py |
| Órdenes | Como admin quiero asignar entregas para cumplir pedidos | Modelo Entrega, relación Conductor-Vehículo | Edward | 12 | Pedidos | El admin asigna conductor y vehículo a cada entrega | ordenes/models.py |
| Transporte | Como conductor quiero ver mis entregas para cumplirlas | Vista de entregas para conductor, actualizar estado | Edward | 10 | Órdenes | El conductor ve su lista y marca como entregado | ordenes/views.py |

**Entregable Sprint 3:** Flujo completo de pedidos, asignación y entrega.

---

## Sprint 4: Facturación, Pagos, Reportes e IA

| Módulo | Historia de Usuario | Tareas Técnicas | Responsable | Horas | Dependencia | Criterio de Aceptación | Evidencia |
|--------|---------------------|-----------------|-------------|-------|-------------|------------------------|-----------|
| Facturación | Como admin quiero generar facturas para los pedidos | Modelo Factura, calcular totales e IVA | Edward | 10 | Sprint 3 | El sistema genera factura automáticamente al confirmar pedido | facturacion/models.py |
| Pagos | Como cliente quiero ver mis pagos para seguimiento | Modelo Pago, relación con Factura, métodos de pago | Edward | 10 | Facturación | El cliente ve su estado de cuenta y pagos | pagos/models.py |
| Reportes | Como admin quiero exportar reportes para análisis | Generar PDF y Excel con ReportLab y openpyxl | Edward | 12 | Facturación + Inventario | El admin descarga reportes de ventas y stock | reportes/views.py |
| IA | Como usuario quiero consultar al asistente IA para ayuda | Integración OpenAI, contexto del sistema | Edward | 15 | - | El usuario envía preguntas y recibe respuestas relevantes | ia/services/llm_service.py |

**Entregable Sprint 4:** Facturación, pagos, reportes y asistente IA completos.
