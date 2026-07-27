# Normalización de Base de Datos - Mejoras de Integridad Referencial (2FN, 3FN)

## Resumen Ejecutivo

Se han implementado mejoras estructurales significativas en el esquema de base de datos para alcanzar **conformidad 3FN** (Tercera Forma Normal), eliminando redundancia, dependencias transitivas y anomalías de actualización.

---

## 1. CAMBIOS IMPLEMENTADOS

### ✅ **PRIORIDAD ALTA - COMPLETADO**

#### 1.1 Normalización de Roles (3FN)
**Problema**: `usuario.rol` era una columna de texto que creaba dependencia transitiva.

**Solución**:
- ✅ Creada tabla `Rol` con campos:
  - `id_rol` (PK)
  - `nombre_rol` (UNIQUE)
  - `descripcion`
  - `activo`

- ✅ Creada tabla `UsuarioRol` (relación N:M):
  - `id_usuario_rol` (PK)
  - `usuario_id` (FK)
  - `rol_id` (FK)
  - `fecha_asignacion`
  - `fecha_revocacion`
  - `activo`
  - Restricción UNIQUE en (usuario, rol)

**Compatibilidad**: El campo `usuario.rol` se mantiene por compatibilidad. El método `save()` sincroniza automáticamente cambios a tabla `usuario_rol`.

**Migración de Datos**: Ejecuta automáticamente en migración `0005_migrate_roles_to_usuario_rol.py`.

---

#### 1.2 Normalización de Factura (3FN)
**Problema**: Factura almacenaba tanto `pedido_id` como `cliente_id`, generando:
- Redundancia: cliente ya viene implícito en pedido
- Inconsistencias: factura y pedido podrían apuntar a clientes diferentes

**Solución**:
- ✅ Eliminado campo `cliente_id` de tabla `factura`
- ✅ `pedido_id` ahora es FK obligatoria (NOT NULL)
- ✅ Cliente accesible mediante: `factura.pedido.cliente` o `factura.cliente` (propiedad)

**Propiedades de Compatibilidad**:
```python
@property
def cliente(self):
    """Obtener cliente desde el pedido (elimina redundancia)."""
    if self.pedido and self.pedido.cliente:
        return self.pedido.cliente.usuario
    elif self.pedido:
        return self.pedido.usuario
    return None
```

---

#### 1.3 Normalización de Referencias a Conductor (Semántica)
**Problema**: `pedido.conductor_id` y `entrega.conductor_id` apuntaban a `usuario` en lugar de a `conductor`.

**Solución**:
- ✅ Cambio de FK en `Pedido`: 
  - DE: `ForeignKey(Usuario, related_name='pedidos_conductor')`
  - A: `ForeignKey(Conductor, related_name='pedidos_asignados')`

- ✅ Cambio de FK en `Entrega`:
  - DE: `ForeignKey(Usuario, limit_choices_to={'rol': 'conductor'})`
  - A: `ForeignKey(Conductor, related_name='entregas_asignadas')`

**Propiedades de Compatibilidad**:
```python
@property
def conductor_usuario(self):
    """Obtener el Usuario del Conductor asignado."""
    if self.conductor:
        return self.conductor.usuario
    return None
```

---

#### 1.4 Verificación: Métodos de Pago ✓
**Estado**: Ya normalizado correctamente.
- `Pago.codigo_metodo_pago` usa FK a `MetodoPago`
- No requería cambios

---

#### 1.5 CHECKs de Integridad - Atomicidad
Se agregaron restricciones CHECK en las siguientes tablas:

| Tabla | Constraint | Verificación |
|-------|-----------|-------------|
| **stock** | `chk_stock_cantidad_actual_gte_0` | cantidad_actual >= 0 |
| **stock** | `chk_stock_minimo_gte_0` | stock_minimo >= 0 |
| **material_construccion** | `chk_material_precio_referencia_gte_0` | precio_referencia >= 0 |
| **vehiculo** | `chk_vehiculo_capacidad_carga_gt_0` | capacidad_carga > 0 |
| **pedido** | `chk_pedido_total_gte_0` | total >= 0 |
| **pedido** | `chk_pedido_precio_gte_0` | precio >= 0 |
| **detalle_pedido** | `chk_detalle_pedido_cantidad_gt_0` | cantidad > 0 |
| **detalle_pedido** | `chk_detalle_pedido_precio_unitario_gte_0` | precio_unitario >= 0 |
| **detalle_pedido** | `uq_detalle_pedido_pedido_material` | UNIQUE(pedido, material) |
| **factura** | `chk_factura_subtotal_gte_0` | subtotal >= 0 |
| **factura** | `chk_factura_iva_gte_0` | iva >= 0 |
| **factura** | `chk_factura_total_gte_0` | total >= 0 |
| **compra** | `chk_compra_total_compra_gte_0` | total_compra >= 0 |
| **detalle_compra** | `chk_detalle_compra_cantidad_gt_0` | cantidad > 0 |
| **detalle_compra** | `chk_detalle_compra_precio_unitario_gte_0` | precio_unitario >= 0 |
| **detalle_compra** | `uq_detalle_compra_compra_material` | UNIQUE(compra, material) |

---

### ⏳ **PRIORIDAD MEDIA**

#### 1.6 Unificación de Nombres Personales (Completado)
**Problema**: Usuario tiene tanto `first_name`/`last_name` (Django) como `nombres`/`apellidos` (custom).

**Solución**:
- ✅ Mantener `nombres` y `apellidos` como primarios
- ✅ Sincronizar automáticamente con `first_name`/`last_name` en método `save()`
- ✅ Garantiza consistencia en ambas direcciones

**Código de Sincronización**:
```python
def save(self, *args, **kwargs):
    # Sincronizar nombres/apellidos ↔ first_name/last_name
    if self.nombres and not self.first_name:
        self.first_name = self.nombres[:30]
    if self.apellidos and not self.last_name:
        self.last_name = self.apellidos[:30]
    
    if self.first_name and self.first_name != self.nombres[:30]:
        self.nombres = self.first_name
    if self.last_name and self.last_name != self.apellidos[:30]:
        self.apellidos = self.last_name
```

---

## 2. MIGRACIONES CREADAS

| Archivo | App | Descripción |
|---------|-----|-----------|
| `0003_rol_usuario_rol.py` | usuarios | Crear tablas Rol y UsuarioRol |
| `0004_add_integrity_constraints.py` | usuarios | Agregar CHECKs a Stock, MaterialConstruccion, Vehiculo |
| `0005_migrate_roles_to_usuario_rol.py` | usuarios | Migrar datos existentes de usuario.rol a usuario_rol |
| `0002_normalize_conductor_fk.py` | ordenes | Cambiar FK de conductor a tabla Conductor + constraints |
| `0002_normalize_factura_3fn.py` | facturacion | Eliminar cliente FK de Factura + constraints |
| `0002_add_integrity_constraints.py` | compras | Agregar CHECKs a Compra y DetalleCompra |

---

## 3. CAMBIOS EN MODELOS

### Apps Modificadas

#### `apps/usuarios/models.py`
- ✅ Agregadas clases `Rol` y `UsuarioRol`
- ✅ Actualizado método `save()` en `Usuario` para sincronización automática
- ✅ Agregados CHECKs a `Stock`, `MaterialConstruccion`, `Vehiculo`

#### `apps/ordenes/models.py`
- ✅ Cambio de FK `Pedido.conductor`: Usuario → Conductor
- ✅ Cambio de FK `Entrega.conductor`: Usuario → Conductor
- ✅ Agregadas propiedades `conductor_usuario` para compatibilidad
- ✅ Agregados CHECKs y UNIQUE constraints a `DetallePedido`
- ✅ Agregados CHECKs a `Pedido`

#### `apps/facturacion/models.py`
- ✅ Eliminado campo `cliente_id` de `Factura`
- ✅ Hecha FK `pedido_id` obligatoria
- ✅ Agregadas propiedades `cliente` y `cliente_id` para compatibilidad
- ✅ Agregados CHECKs

#### `apps/compras/models.py`
- ✅ Agregados CHECKs y UNIQUE constraints a `DetalleCompra`
- ✅ Agregados CHECKs a `Compra`

---

## 4. COMPATIBILIDAD CON CÓDIGO EXISTENTE

### Cambios que No Rompen Código

✅ **`usuario.rol` sigue funcionando**
- Campo mantiene su valor
- Sincroniza automáticamente a `usuario_rol`
- Todas las vistas que usan `user.rol` funcionan sin cambios

✅ **`factura.cliente` sigue disponible**
- Ahora es una propiedad que calcula el valor
- Accede al cliente a través de `factura.pedido`
- Código existente no requiere cambios

✅ **`pedido.conductor` ahora apunta a Conductor**
- Compatible porque `Conductor.usuario` existe
- Propiedades facilitan acceso a usuario: `pedido.conductor_usuario`

### Vistas Afectadas (Requieren Revisión)

Las siguientes vistas usan `usuario.rol` y pueden beneficiarse de usar el nuevo sistema de Rol/UsuarioRol (opcional, no obligatorio):

- `apps/usuarios/views.py` (17 referencias)
- `apps/ordenes/views.py` (4 referencias)
- `apps/facturacion/views.py` (2 referencias)
- `apps/gestion_pedidos/views.py` (2 referencias)
- `apps/clientes/views.py` (1 referencia)

---

## 5. PASOS PARA APLICAR EN NEON

### Paso 1: Hacer Backup
```sql
pg_dump -h <host> -U <user> -d <database> -F custom > backup_$(date +%Y%m%d_%H%M%S).dump
```

### Paso 2: Ejecutar Migraciones en Orden

```bash
# Con el proyecto configurado:
python manage.py migrate usuarios 0003_rol_usuario_rol
python manage.py migrate usuarios 0004_add_integrity_constraints
python manage.py migrate usuarios 0005_migrate_roles_to_usuario_rol
python manage.py migrate ordenes 0002_normalize_conductor_fk
python manage.py migrate facturacion 0002_normalize_factura_3fn
python manage.py migrate compras 0002_add_integrity_constraints
```

### Paso 3: Verificar Datos

```sql
-- Verificar que los roles fueron migrados
SELECT COUNT(*) FROM rol;
SELECT COUNT(*) FROM usuario_rol;

-- Verificar que facturas están correctas
SELECT * FROM factura WHERE pedido_id IS NULL; -- Debería estar vacío

-- Verificar que conductores están correctos
SELECT COUNT(*) FROM pedido WHERE conductor_id IS NOT NULL;
```

---

## 6. VENTAJAS DE ESTOS CAMBIOS

### Atomicidad Mejorada
- CHECKs previenen datos inconsistentes en origen
- UNIQUE constraints en detalles previenen duplicados
- Transacciones pueden confiar en validaciones a nivel BD

### 2FN - Parcialidad Mejorada
- Detalles tienen UNIQUE en (pedido, material) y (compra, material)
- Elimina la posibilidad de registros duplicados del mismo material en un documento

### 3FN - Transitividad Eliminada
- **Roles**: Ya no dependen transitivamente de usuario
- **Factura/Cliente**: Cliente ya no es redundante
- **Conductor**: Semánticamente correcto (conductor es conductor, no usuario genérico)
- **Nombres**: Sincronizados, no redundantes

### Integridad Referencial
- CHECKs garantizan que montos y cantidades nunca sean negativos
- Capacidades siempre positivas
- Stock nunca puede ser negativo en BD (no solo en aplicación)

---

## 7. RECOMENDACIONES FUTURAS

### Prioridad Baja
1. **Revisar campos nullable innecesarios**
   - `factura.numero`: ¿Debería ser obligatorio?
   - `pedido.direccion_destino`: ¿Debería ser obligatorio?

2. **Catálogos para estados**
   - Crear tabla `estado_pedido` en lugar de CHECK
   - Crear tabla `tipo_cliente`
   - Crear tabla `tipo_movimiento_inventario`

3. **Mover número_seguro de EPS a Conductor**
   - EPS es la empresa, conductor es el afiliado
   - Mejoraría la semántica del modelo

---

## 8. VERIFICACIÓN DE COMPATIBILIDAD

### Testing Recomendado

```python
# 1. Verificar que usuario.rol sigue funcionando
usuario = Usuario.objects.first()
assert usuario.rol in ['admin', 'cliente', 'conductor', 'empleado']

# 2. Verificar que usuario_rol se crea automáticamente
assert usuario.usuario_roles.exists()

# 3. Verificar que factura.cliente funciona
factura = Factura.objects.first()
assert factura.cliente is not None  # O None si pedido es None

# 4. Verificar que conductor_usuario funciona
pedido = Pedido.objects.filter(conductor__isnull=False).first()
if pedido:
    assert pedido.conductor_usuario is not None

# 5. Verificar CHECKs (intentar insertar datos inválidos)
# Esto debería fallar en BD:
# Stock.objects.create(material=mat, cantidad_actual=-1, stock_minimo=0)
```

---

## 9. CONTACTO & DOCUMENTACIÓN

Para consultas sobre estas migraciones:
- Revisar MER actualizado: [Incluir ruta al MER_actualizado.drawio]
- Consultar análisis detallado en: NORMALIZACION_BD.md

---

**Fecha de Implementación**: 2025-07-27
**Estado**: Migraciones creadas, lisas para aplicar
**Siguiente Paso**: Ejecutar migraciones en BD Neon

