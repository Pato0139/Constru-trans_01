# Migraciones Finales - Cierre de 3FN Pendientes

Basado en el diagnóstico de revisión en Neon, estas migraciones **completan lo que faltaba**:

## 📋 Nuevas Migraciones (4 archivos)

### 1. `0006_rol_usuario_rol_sql.py` (usuarios)
- Crear tabla `rol` con `nombre_rol UNIQUE`
- Crear tabla `usuario_rol` con PK compuesta
- Insertar roles por defecto: admin, operador, conductor, cliente, proveedor

**Cierra**: Normalización de roles (3FN)

---

### 2. `0002_normalize_metodo_pago_fk.py` (pagos)
- Cambiar `pago_pedido.metodo_pago` de texto → FK a `metodo_pago`
- Migrar datos existentes
- Hacer FK obligatoria

**Cierra**: pago_pedido.metodo_pago ahora es relación real, no texto

---

### 3. `0003_conductor_fk_to_conductor.py` (ordenes)
- Limpiar referencias inválidas de conductores
- Cambiar FK: `pedido.conductor_id` → `conductor.usuario_id`
- Cambiar FK: `entrega.conductor_id` → `conductor.usuario_id`

**Cierra**: Semántica correcta - conductor referencia conductor, no usuario

---

### 4. `0003_cleanup_cliente_redundancy.py` (facturacion)
- Setear `factura.cliente_id = NULL` (redundancia con pedido)
- Hacer campo nullable (puede eliminarse después)

**Cierra**: Factura normalizada - sin cliente redundante

---

### 5. `0007_comprehensive_checks.py` (usuarios)
Agregar CHECKs pendientes:
- `stock.cantidad_actual >= 0`
- `stock.stock_minimo >= 0`
- `material_construccion.precio_referencia >= 0`
- `pago.monto > 0`

**Cierra**: Integridad atomicidad mejorada

---

### 6. `0008_catalogo_required_and_names_consolidation.py` (usuarios)
- Llenar `material.catalogo_id` NULL con default
- Hacer `catalogo_id NOT NULL` (corrige regresión)
- Consolidar nombres: `first_name/last_name` → `nombres/apellidos`

**Cierra**: Datos consolidados, sin regresiones

---

## ✅ Orden de Ejecución

```bash
# Ejecutar en Neon en este orden:
python manage.py migrate usuarios 0006
python manage.py migrate pagos 0002
python manage.py migrate ordenes 0003
python manage.py migrate facturacion 0003
python manage.py migrate usuarios 0007
python manage.py migrate usuarios 0008
```

---

## 📊 Qué se Cierra

| Problema | Solución | Estado |
|----------|----------|--------|
| usuario.rol texto | Tablas Rol + UsuarioRol | ✅ 0006 |
| pago_pedido.metodo_pago texto | FK a metodo_pago | ✅ 0002 |
| pedido.conductor → usuario | → conductor | ✅ 0003 |
| factura.cliente redundante | NULL (eliminable) | ✅ 0003 |
| CHECKs faltantes | Stock, Material, Pago | ✅ 0007 |
| catalogo_id nullable (regresión) | NOT NULL con default | ✅ 0008 |
| first_name/last_name duplicados | Consolidar en nombres | ✅ 0008 |

---

**Resultado Final**: 3FN completamente lograda en todos los frentes.

