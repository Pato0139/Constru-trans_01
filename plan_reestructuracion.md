# Plan de Reestructuración Final — Constru-Trans

## Tabla objetivo (del PDF `l.pdf`)

| App (carpeta) | Modelos | Responsabilidad |
|---|---|---|
| **usuarios** | Usuario | Usuarios, autenticación y roles |
| **catalogo** | Categoria, Marca, UnidadMedida, Producto | Catálogo, precios y stock |
| **compras** | Proveedor, ProveedorProducto, Compra, DetalleCompra | Abastecimiento a proveedores |
| **pedidos** | Pedido, DetallePedido | Pedidos de clientes |
| **pagos** | Pago, DetallePago | Pagos y comprobante |
| **logistica** | Vehiculo, Envio, Novedad | Transporte y entregas |
| **auditoria** | Bitacora | Registro de acciones relevantes |

---

## Mapeo detallado: Estado actual → Estado deseado

### 1. `usuarios/` → se **mantiene** pero se **adelgaza**

**Actualmente contiene** (en `usuarios/models.py`):
- ✅ Usuario, Rol, UsuarioRol, EPS, Conductor — **Se quedan aquí**
- ❌ Vehiculo, ConductorVehiculo — **Se mueven a `logistica/`**
- ❌ Catalogo, UnidadMedida, Marca, MaterialConstruccion, Stock, HistorialPrecioMaterial — **Se mueven a `catalogo/`**
- ❌ Proveedor — **Se mueve a `compras/`**
- ❌ Notificacion — **Se queda en `usuarios/` (auxiliar)** o se elimina si no se usa

**Views, urls, templates, forms, admin** → Se mantienen adaptados al nuevo scope.

### 2. `inventario/` → se **renombra** a `catalogo/`

**Contenido actual de `inventario/`**: views de materiales, stock, movimientos, conteo, sincronización.

**Lo que absorbe `catalogo/`**:
- Los modelos que estaban en `usuarios/`: Catalogo, Marca, UnidadMedida, MaterialConstruccion, Stock, HistorialPrecioMaterial
- Todo el contenido actual de `inventario/` (views, templates, urls, services, tests, management commands)

### 3. `compras/` → se **mantiene**

**Actualmente contiene**: Compra, ProveedorMaterial, DetalleCompra.

**Se le agrega**: Proveedor (que estaba en `usuarios/models.py`).

### 4. `ordenes/` + `gestion_pedidos/` → se **fusionan** en `pedidos/`

**`ordenes/` contiene**: Pedido, DetallePedido, Entrega (que se moverá a `logistica/`)
**`gestion_pedidos/` contiene**: SolicitudPedido, DetalleSolicitudPedido

**`pedidos/` tendrá**: Pedido, DetallePedido, SolicitudPedido, DetalleSolicitudPedido + views de ambas apps.
- La `Entrega` que está en `ordenes/` se mueve a `logistica/`.

### 5. `pagos/` → se **mantiene** (absorbe `facturacion/` si existe)

### 6. `transporte/` + `novedades/` + parte de `ordenes/` → se **fusionan** en `logistica/`

**Contenido nuevo de `logistica/`**:
- Vehiculo, ConductorVehiculo (de `usuarios/`)
- Entrega (de `ordenes/`)
- Novedad, Seguimiento, RespuestaSeguimiento (de `novedades/`)
- Views de `transporte/` (lista_vehiculos, crear, editar, eliminar)
- Views y templates de `novedades/`
- Templates de `transporte/` y `novedades/`

### 7. `historial/` → se **renombra** a `auditoria/`

Todo el contenido de `historial/` se mueve a `auditoria/`.

### 8. Apps que se mantienen sin cambios
- `core/` — Configuración central
- `ia/` — Asistente IA
- `inicio/` — Página de inicio
- `licensing/` — Licenciamiento
- `ayuda/` — Ayuda
- `reportes/` — Reportes
- `clientes/` — Se mantiene (perfil de cliente, views de clientes)

---

## Archivos a modificar centrales

| Archivo | Cambio |
|---|---|
| `core/settings/base.py` | `LOCAL_APPS`: quitar apps viejas, poner nuevas |
| `core/urls.py` | Actualizar includes con nuevos nombres de módulo |
| `core/routers.py` | Actualizar `APPS_NUBE` con nombres nuevos |
| `core/middleware.py` | Actualizar referencias a namespace de apps |
| Todos los `apps.py` | Actualizar `name` y `label` |
| Todos los imports cross-app | Actualizar path de imports |
| Templates `{% url %}` | Actualizar namespaces |

---

## Orden de ejecución

> [!IMPORTANT]
> **Estrategia**: Crear las nuevas carpetas con la estructura correcta, copiar el contenido adaptado, actualizar imports/settings, y finalmente eliminar las carpetas viejas.

### Fase 1 — Crear nuevas apps
1. Crear `catalogo/` con modelos de inventario + catálogo/material/stock de usuarios
2. Crear `pedidos/` fusionando ordenes + gestion_pedidos (sin Entrega)
3. Crear `logistica/` fusionando transporte + novedades + Entrega + Vehiculo
4. Crear `auditoria/` con contenido de historial

### Fase 2 — Mover modelos
5. Mover modelos de `usuarios/models.py` a sus nuevas apps
6. Mover Proveedor a `compras/`
7. Mantener `db_table` en Meta para NO romper la BD

### Fase 3 — Actualizar referencias
8. Actualizar `core/settings/base.py`
9. Actualizar `core/urls.py`
10. Actualizar `core/routers.py`
11. Actualizar imports en todas las apps
12. Actualizar templates con nuevos namespaces

### Fase 4 — Limpieza
13. Eliminar carpetas viejas: `inventario/`, `ordenes/`, `gestion_pedidos/`, `transporte/`, `novedades/`, `historial/`
14. Correr `python manage.py check` para verificar
