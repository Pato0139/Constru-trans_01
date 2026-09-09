# CONSTRU-TRANS

Documentación actualizada basada en la versión real del proyecto que existe en el repositorio y en la configuración activa de Django.

> Fuente de verdad: la configuración de Django en `core/settings/base.py`, los modelos activos en cada app y los servicios implementados en el código actual. No se incluye funcionalidad inventada ni referencias a módulos que no están activos en la aplicación real.

---

## 1. Descripción general del proyecto

Constru-Trans es un sistema web desarrollado en Django para gestionar operaciones relacionadas con usuarios, clientes, inventario, compras, pedidos, facturación, pagos, reportes y asistente IA interno. El proyecto está organizado como una aplicación modular con varios apps locales registradas en `INSTALLED_APPS` y con una capa de seguridad propia para restricción por roles y bloqueo de IP.

El sistema actual no es un ERP genérico completo con múltiples módulos de negocio no implementados. La base real del código corresponde a una plataforma de gestión operativa para una empresa de materiales de construcción y transporte, con foco en control interno, facturación y asistencia basada en contexto local.

---

## 2. Alcance real del sistema

### 2.1 Apps activas en Django

La configuración activa del proyecto incluye estas apps:

- `core`
- `usuarios`
- `clientes`
- `inventario`
- `compras`
- `ordenes`
- `gestion_pedidos`
- `facturacion`
- `pagos`
- `reportes`
- `inicio`
- `historial`
- `transporte`
- `licensing`
- `ia`
- `ayuda`
- `novedades`

Las carpetas bajo `apps/` no se consideran parte del alcance activo del proyecto si no están registradas en la configuración principal de Django.

### 2.2 Funcionalidades realmente implementadas

- Gestión de usuarios, roles y autenticación.
- Registro y administración de clientes y perfiles asociados.
- Gestión de materiales, stock, movimientos y conteos de inventario.
- Compras a proveedores y detalle de compra.
- Gestión de pedidos y solicitudes de pedido.
- Gestión de órdenes, entregas y transporte asociado.
- Facturación con estados `pendiente`, `pagada` y `anulada`.
- Registro de pagos y seguimiento de saldos pendientes.
- Generación de reportes PDF y Excel.
- Historial de actividades y auditoría.
- Seguridad por roles, IP y eventos de seguridad.
- Asistente IA interno con acceso a contexto local y datos de negocio.
- Licenciamiento y control de acceso a la instalación.

### 2.3 Funcionalidades que no forman parte del alcance real verificado

Se han eliminado del documento referencias a:

- RAG o recuperación aumentada de contexto.
- Memoria semántica.
- Embeddings.
- Vector database.
- Agentes autónomos con herramientas externas.
- APIs externas de IA no documentadas en el código.
- Entidades que no existen como modelos reales activos.

La IA implementada en este proyecto es local, integrada en Django y orientada a consultar contexto del sistema y responder con información del negocio, no un sistema de agentes externos ni un motor vectorial.

---

## 3. Arquitectura técnica

### 3.1 Stack principal

- Python
- Django 5.1.5
- PostgreSQL opcional vía `DATABASE_URL`
- SQLite como base por defecto local
- Django REST Framework
- ReportLab para PDF
- OpenPyXL para Excel
- django-environ para configuración
- Celery + Redis para procesos asíncronos y colas
- Seguridad con django-axes, django-ratelimit, django-otp, argon2, django-csp

### 3.2 Configuración de entorno y base de datos

El proyecto usa un archivo `.env` para configurar variables de entorno. La configuración actual de `core/settings/base.py` define:

- `DATABASES["default"]` como SQLite local.
- `DATABASES["local"]` como SQLite local.
- `DATABASES["remota"]` solo si `DATABASE_URL` está definido.
- Router de base de datos `core.routers.EnrutadorInventario` para separar lógica de inventario.

Esto significa que la base local es la opción predeterminada y la remota es una configuración opcional para despliegue o sincronización.

### 3.3 Seguridad implementada

El proyecto cuenta con una capa de seguridad centralizada en `core/security.py` y `core/middleware.py`:

- Bloqueo de IP por accesos no autorizados repetidos.
- Registro de `SecurityEvent`.
- `role_required` para control de acceso por rol.
- `RoleNamespaceMiddleware` para filtrar acceso por namespace y url_name.
- Protección a vistas administrativas y de cliente según rol.

### 3.4 IA y asistente del proyecto

La app `ia` contiene servicios y configuración para un asistente interno del negocio. La integración actual se apoya en:

- Cliente Python de OpenAI.
- Endpoint local compatible con Ollama o modelo local configurado en variables de entorno.
- Servicios de contexto para reunir datos de pedidos, inventario, facturación y clientes.
- Plantillas y historial de conversaciones en modelos de Django.

La intención funcional corresponde a un asistente inteligente del negocio integrado en la plataforma, con acceso a contexto del sistema y datos operativos. No se documenta una implementación de RAG, memoria semántica o base vectorial en la lectura actual del código.

---

## 4. Modelo de dominio real

Los modelos que aparecen en el código actual y se usan como fuente de verdad son los siguientes:

### 4.1 Usuarios y perfiles

- `Usuario`
- `Rol`
- `Conductor`
- `Vehiculo`
- `Proveedor`
- `MaterialConstruccion`
- `Stock`
- `MetodoPago`
- `Notificacion`

### 4.2 Clientes

- `Cliente`
- `ClienteVIP`

### 4.3 Compras e inventario

- `Compra`
- `ProveedorMaterial`
- `DetalleCompra`
- `MovimientoInventario`
- `LoteMaterial`
- `SesionConteo`
- `ConteoItem`

### 4.4 Pedidos, entregas y gestión

- `Pedido`
- `DetallePedido`
- `Entrega`
- `SolicitudPedido`
- `DetalleSolicitudPedido`

### 4.5 Facturación y pagos

- `Factura`
- `Pago`
- `PagoPedido`

La factura es una entidad real del proyecto, con flujo de pagos y estados de facturación. No es un concepto documental inventado sin modelo asociado.

### 4.6 Reportes, historial, novedades e IA

- `Reporte`
- `HistorialReporte`
- `Historial`
- `Novedad`
- `Seguimiento`
- `RespuestaSeguimiento`
- `ConversationHistory`
- `ConversationMessage`
- `AIPromptTemplate`
- `AIConfiguration`
- `KnowledgeBase`

### 4.7 Equivalencias de nomenclatura entre documento y código

Durante el desarrollo se produjeron ajustes de terminología normal entre el documento funcional y la implementación final. Estas equivalencias no cambian el alcance del sistema y mantienen la misma intención de negocio:

- `Producto` / `Categoria` / `Marca` del documento corresponden funcionalmente a `MaterialConstruccion` y `Catalogo`, con control adicional de `UnidadMedida` y `Stock`.
- `Pedido` / `DetallePedido` se implementan con el módulo de `gestion_pedidos` y con la lógica administrativa de `ordenes`, manteniendo el mismo propósito de registrar materiales, calcular totales y controlar estados.
- `Envio` se asocia operativamente a `Entrega`, que es el término usado en el código para el flujo de transporte y seguimiento.
- `Bitácora` se consolida en el módulo `historial`, que registra usuario, acción, IP, fecha y contexto de la operación.
- La facturación se implementa con un módulo dedicado `facturacion`, con `Factura` como entidad principal para mayor trazabilidad y control de pagos.
- El asistente inteligente del documento corresponde al módulo `ia`, con contexto del negocio y configuración de integración local para modelos compatibles con OpenAI.

Estas variantes son de nomenclatura y no implican diferencias funcionales significativas ni pérdida de requerimientos.

### 4.8 Licenciamiento y seguridad

- `Installation`
- `Licencia`
- `UsuarioLicencia`
- `AuditoriaLicencia`
- `BloqueoIP`
- `SecurityEvent`

---

## 5. Requisitos funcionales actuales

### 5.1 Épicas del sistema

#### Épica 1 – Gestión de usuarios y acceso
Entidades relacionadas: `Usuario` y `Rol`. Permite administrar los usuarios del sistema y controlar el acceso a las funcionalidades de Constru-Trans mediante autenticación y asignación de roles (`admin`, `cliente`, `conductor`, `empleado`). El sistema permite registrar, consultar y actualizar información de usuarios, además de gestionar inicio y cierre de sesión y recuperación de contraseña.

#### Épica 2 – Gestión de materiales e inventario
Entidades relacionadas: `MaterialConstruccion`, `Catalogo`, `UnidadMedida` y `Stock`. Permite administrar los materiales utilizados por la operación, organizándolos por catálogos y unidades de medida. Incluye el registro, consulta y actualización de materiales, así como el control riguroso de existencias mediante el stock asociado a cada material.

#### Épica 3 – Gestión de pedidos y órdenes
Entidades relacionadas: `Pedido`, `DetallePedido` y `Orden`. Permite gestionar los pedidos realizados por los clientes dentro del sistema, incluyendo materiales solicitados, cantidades, precios, fechas y estados. A nivel administrativo, este proceso se controla mediante el módulo de órdenes para su facturación y despacho. El sistema permite consultar, modificar, aprobar y cancelar pedidos según el flujo operativo definido.

#### Épica 4 – Gestión de entregas y transporte
Entidades relacionadas: `Entrega`, `Vehiculo`, `Novedad` y `Conductor`. Permite administrar el transporte de los pedidos mediante la asignación de vehículos y conductores, así como el seguimiento de entregas y el registro de novedades asociadas a incidentes operativos.

#### Épica 5 – Gestión de compras y proveedores
Entidades relacionadas: `Compra`, `DetalleCompra` y `Proveedor`. Permite registrar y consultar compras realizadas para abastecimiento del inventario, junto con materiales, cantidades, precios y fechas. La recepción de compras puede actualizar el stock si la lógica del flujo así lo requiere.

#### Épica 6 – Gestión de pagos y facturación
Entidades relacionadas: `Pago`, `Factura` y `MetodoPago`. Permite registrar y consultar los pagos asociados a pedidos y controlar la facturación de las operaciones. El sistema gestiona facturas digitales con estados de negocio y trazabilidad de pagos según el método usado.

#### Épica 7 – Auditoría, historial y novedades
Entidades relacionadas: `Historial` y `Novedad`. Permite mantener un registro de las actividades realizadas dentro del sistema y de las novedades asociadas a entregas y procesos de negocio. El historial registra usuario, acción, IP, fecha y módulo, facilitando la auditoría y trazabilidad operativa.

#### Épica 8 – Asistente inteligente (IA)
Funcionalidad relacionada: módulo `ia`. Permite a los usuarios consultar información del negocio y recibir respuestas basadas en contexto del sistema. La funcionalidad está integrada dentro de la aplicación y se apoya en servicio de IA local con contexto operativo, sin constituir un modelo independiente o una infraestructura de base vectorial en la implementación revisada.

### 5.2 Historias de usuario clave

#### Gestión de materiales e inventario
- HU-08: Como administrador, quiero registrar materiales de construcción para administrar el inventario disponible en el sistema.
- HU-09: Como administrador, quiero organizar los materiales por catálogos o tipos para facilitar su clasificación.
- HU-11: Como administrador, quiero administrar las unidades de medida para registrar correctamente las cantidades.
- HU-12: Como usuario autorizado, quiero consultar los materiales disponibles para conocer su información y existencia.
- HU-13: Como administrador, quiero actualizar la información de los materiales para mantener al día el catálogo.
- HU-14: Como usuario autorizado, quiero consultar el stock de los materiales para conocer su disponibilidad antes de realizar una operación.

#### Gestión de pedidos y órdenes
- HU-15: Como cliente, quiero crear un pedido seleccionando materiales para solicitar lo que necesito.
- HU-16: Como cliente, quiero agregar materiales a un pedido para especificar cantidades.
- HU-17: Como administrador, quiero gestionar el flujo de la orden y su estado para controlar aprobación, despacho y seguimiento.

#### Gestión de entregas y transporte
- HU-23: Como administrador, quiero registrar y administrar vehículos para controlar la flota.
- HU-24: Como administrador, quiero crear entregas asociadas a órdenes aprobadas para organizar el despacho.
- HU-25: Como administrador, quiero asignar un conductor y un vehículo a una entrega para gestionar el transporte.
- HU-26: Como conductor o administrador, quiero consultar las entregas registradas para realizar el seguimiento en ruta.
- HU-27: Como conductor, quiero registrar novedades asociadas a una entrega para documentar incidentes.

#### Gestión de pagos y facturación
- HU-38: Como sistema, quiero generar automáticamente una factura cuando la entrega o la operación correspondiente esté confirmada para entregar soporte digital.
- HU-39: Como usuario, quiero consultar o descargar la factura generada en el formato disponible por el sistema.

#### Auditoría, historial y novedades
- HU-40: Como sistema, quiero registrar las acciones relevantes en el historial para la trazabilidad.
- HU-41: Como administrador, quiero consultar el historial cronológico para realizar auditorías operativas.

### 5.3 Tareas de implementación asociadas

#### Materiales e inventario
- T-11: Crear modelo `MaterialConstruccion`.
- T-12: Crear modelo `Catalogo`.
- T-14: Crear modelo `UnidadMedida`.
- T-15: Implementar CRUD de materiales.
- T-20: Implementar modelo `Stock` y su vinculación al material.

#### Pedidos y órdenes
- T-23: Crear módulo y modelo `Pedido` y lógica administrativa de `Orden`.
- T-26: Implementar asociación de materiales a pedidos mediante `DetallePedido`.

#### Entregas y transporte
- T-36: Crear modelo `Vehiculo` y perfil de `Conductor`.
- T-37: Crear modelo `Entrega`.
- T-38: Crear modelo `Novedad`.

#### Pagos y facturación
- T-54: Crear modelo `Pago` y modelo `Factura`.
- T-61: Implementar generación automática de la factura al finalizar la entrega o operación asociada.

#### Auditoría e historial
- T-63: Crear módulo de auditoría `Historial`.
- T-64: Registrar usuario, IP y módulo afectado en cada acción relevante.

### 5.4 Requerimientos funcionales ajustados

- RF5: El sistema debe permitir registrar materiales ingresando nombre, precio, stock inicial y catálogo.
- RF6: El sistema debe permitir administrar catálogos y unidades de medida.
- RF10: El sistema debe permitir registrar materiales, cantidades y precios asociados a cada pedido.
- RF18: El sistema debe permitir crear entregas asociadas a pedidos, asignando conductor y vehículo.
- RF22: El sistema debe generar y almacenar facturas digitales automáticas al confirmar la operación o entrega asociada.
- RF23: El sistema debe registrar las acciones en un historial automático con usuario, fecha, módulo e IP, para auditoría del sistema.

---

## 6. Requisitos no funcionales

- Arquitectura modular en Django.
- Seguridad por roles y validación de IP.
- Gestión de variables de entorno con archivos `.env`.
- Base local con posibilidad de base remota premium via `DATABASE_URL`.
- Separación de responsabilidades entre apps y servicios.
- Preparación para despliegue con políticas de seguridad, cache y automatización.

---

## 7. Estructura del proyecto

La estructura global del repositorio incluye:

- `core/`: configuración central, seguridad, middleware y routers.
- `usuarios/`: autenticación, roles, usuarios y catálogo de materiales.
- `clientes/`: gestión de clientes.
- `inventario/`: materiales, stock y movimientos.
- `compras/`: compras y proveedores.
- `ordenes/`: órdenes y entregas.
- `gestion_pedidos/`: solicitudes y detalle.
- `facturacion/`: facturas y pagos asociados.
- `pagos/`: registro de pagos.
- `reportes/`: reportes y exportación PDF/Excel.
- `historial/`: auditoría.
- `transporte/`: organización de vehículos y conductores.
- `licensing/`: licenciamiento del sistema.
- `ia/`: asistentes, templates, configuración y contexto.
- `ayuda/`: ayuda y soporte interno.
- `novedades/`: gestión de novedades y seguimientos.
- `templates/`: plantillas base del frontend.

---

## 8. Observaciones importantes

1. La documentación debe basarse en el código real y no en supuestos legacy.
2. La app `ia` es un asistente integrado al proyecto y no una infraestructura externa con vector DB.
3. La base por defecto es SQLite; la base remota PostgreSQL es opcional y configurable.
4. La facturación es una entidad real del sistema y su estado se gestiona en la lógica de negocio.
5. El proyecto cuenta con validaciones de seguridad y control de acceso explícitas en middleware y decoradores.

---

## CAMBIOS REALIZADOS EN LA DOCUMENTACIÓN

Se actualizaron los documentos para alinear la documentación con el código real del repositorio y eliminar información no verificada.

### Cambios principales

- Se corrigió la lista de apps activas para que coincida con `INSTALLED_APPS` de Django.
- Se ajustó la terminología del dominio para reflejar los nombres reales usados en el código: `MaterialConstruccion`, `Catalogo`, `Entrega`, `Historial`, y `Factura`.
- Se incorporó una sección de equivalencias entre el documento de requisitos y la implementación para evitar contradicciones de nombres en la sustentación.
- Se actualizó la descripción de IA para reflejar una integración local con contexto del negocio y modelos compatibles con OpenAI/Ollama, sin inventar capacidades no observadas en el código.
- Se corrigió la descripción de la base de datos para indicar claramente que SQLite es la opción por defecto y PostgreSQL solo es opcional mediante `DATABASE_URL`.
- Se revisó la parte de facturación para reflejar la entidad `Factura` real y sus estados de negocio.
- Se eliminaron menciones a módulos heredados o no activos que no forman parte de la configuración actual del proyecto.
- Se ajustó el alcance funcional para describir únicamente aquellas funciones verificadas en modelos, vistas, servicios y configuraciones reales.
- Se añadió la sección de “Cambios realizados en la documentación” para dejar constancia del ajuste de contenido realizado sobre la fuente de verdad del proyecto actual.

---

Este documento se considera la versión actualizada y coherente con el estado real del repositorio en este momento.
