# ✅ CHECKLIST DE IMPLEMENTACIÓN - NORMALIZACIÓN BD

## FASE 1: PREPARACIÓN (Antes de aplicar)

### 1.1 Respaldo
- [ ] Hacer backup full de BD Neon: `pg_dump ... > backup_20250727.dump`
- [ ] Guardar backup en lugar seguro (Google Drive, S3, etc.)
- [ ] Anotar URL de conexión Neon actual
- [ ] Verificar que backup se restaura correctamente (probar en BD de test)

### 1.2 Ambiente Local
- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Configurar `.env` con DB local (opcional pero recomendado)
- [ ] Probar migraciones en BD local primero
- [ ] Ejecutar tests locales: `python manage.py test`

### 1.3 Revisar Cambios
- [ ] Leer [CAMBIOS_NORMALIZACION_BD.md](./CAMBIOS_NORMALIZACION_BD.md)
- [ ] Leer [RESUMEN_VISUAL_NORMALIZACION.md](./RESUMEN_VISUAL_NORMALIZACION.md)
- [ ] Revisar migraciones en [apps/usuarios/migrations/](./apps/usuarios/migrations/)
- [ ] Revisar migraciones en [apps/ordenes/migrations/](./apps/ordenes/migrations/)
- [ ] Revisar migraciones en [apps/facturacion/migrations/](./apps/facturacion/migrations/)
- [ ] Revisar migraciones en [apps/compras/migrations/](./apps/compras/migrations/)

### 1.4 Código
- [ ] Confirmar que cambios en modelos están en lugar
- [ ] Verificar que método `save()` de Usuario está implementado
- [ ] Verificar propiedades en Factura (`cliente`, `cliente_id`)
- [ ] Verificar propiedades en Pedido (`conductor_usuario`)

---

## FASE 2: PRUEBAS LOCALES (En BD Local)

### 2.1 Migraciones Secuencial
```bash
# Usuario
python manage.py migrate usuarios 0003
✓ Verificar que tablas rol y usuario_rol se crearon
✓ Verificar struktur en BD: \dt rol, \dt usuario_rol

python manage.py migrate usuarios 0004
✓ Verificar CHECKs agregados

python manage.py migrate usuarios 0005
✓ Verificar que usuario_rol se pobló automáticamente
✓ SELECT COUNT(*) FROM usuario_rol; -- Debería > 0
```

- [ ] Migración 0003: Rol y UsuarioRol creadas
- [ ] Migración 0004: CHECKs en Stock, Material, Vehiculo
- [ ] Migración 0005: Datos migrados a usuario_rol

### 2.2 Migraciones Órdenes
```bash
python manage.py migrate ordenes 0002
✓ Verificar que conductor_id apunta a conductor (no usuario)
✓ Verificar constraints en pedido y detalle_pedido
```

- [ ] FK de conductor actualizada en Pedido
- [ ] FK de conductor actualizada en Entrega
- [ ] CHECKs en Pedido agregados
- [ ] UNIQUE en DetallePedido agregado

### 2.3 Migraciones Facturación
```bash
python manage.py migrate facturacion 0002
✓ Verificar que cliente_id fue eliminado de factura
✓ SELECT * FROM factura WHERE pedido_id IS NULL; -- Debería estar vacío
```

- [ ] Campo cliente eliminado de Factura
- [ ] FK pedido_id ahora obligatoria (NOT NULL)
- [ ] CHECKs en Factura agregados

### 2.4 Migraciones Compras
```bash
python manage.py migrate compras 0002
✓ Verificar CHECKs en Compra y DetalleCompra
```

- [ ] CHECKs en Compra agregados
- [ ] CHECKs en DetalleCompra agregados
- [ ] UNIQUE en DetalleCompra agregado

---

## FASE 3: TESTS DE DATOS (Verificar integridad)

### 3.1 Verificar Rol y UsuarioRol
```sql
-- Estos comandos ejecutar en BD local
SELECT COUNT(*) FROM rol;                    -- Debería ser 4 (admin, cliente, conductor, empleado)
SELECT COUNT(*) FROM usuario_rol;           -- Debería ser = a COUNT(*) FROM usuario
SELECT * FROM rol;                          -- Ver todas los roles
SELECT usuario_id, COUNT(*) FROM usuario_rol GROUP BY usuario_id; -- Verificar distribución
```

- [ ] Tabla `rol` tiene 4 registros
- [ ] Tabla `usuario_rol` tiene datos para todos los usuarios
- [ ] No hay usuarios sin roles

### 3.2 Verificar Factura
```sql
-- Estos comandos ejecutar en BD local
SELECT COUNT(*) FROM factura WHERE pedido_id IS NULL;  -- Debería ser 0
SELECT * FROM factura LIMIT 5;                          -- Ver estructura (sin cliente_id)
-- Intentar insertar factura sin pedido (debe fallar):
-- INSERT INTO factura (numero, fecha, estado) VALUES ('TEST', NOW(), 'pendiente'); -- ❌ Error esperado
```

- [ ] No hay facturas sin pedido
- [ ] Estructura de factura correcta (sin cliente_id)
- [ ] NOT NULL constraint en pedido_id funciona

### 3.3 Verificar Conductor FK
```sql
-- Estos comandos ejecutar en BD local
SELECT COUNT(*) FROM pedido WHERE conductor_id IS NOT NULL;                    -- Ver cuántos tienen conductor
SELECT p.conductor_id, c.usuario_id FROM pedido p JOIN conductor c ON p.conductor_id = c.usuario_id LIMIT 5; 
-- Si esto falla, FK está mal
```

- [ ] FK de conductor funciona correctamente
- [ ] No hay integridad referencial rota

### 3.4 Verificar CHECKs
```sql
-- Intentar insertar datos inválidos (todos deben fallar):

-- ❌ Stock negativo:
UPDATE stock SET cantidad_actual = -1 WHERE material_id = 1; -- ❌ Error esperado

-- ❌ Precio negativo:
UPDATE material_construccion SET precio_referencia = -100 WHERE cod_material = 1; -- ❌ Error esperado

-- ❌ Capacidad negativa:
UPDATE vehiculo SET capacidad_carga = 0 WHERE id_vehiculo = 1; -- ❌ Error esperado

-- ❌ Detalle duplicado:
INSERT INTO detalle_pedido (pedido_id, material_id, cantidad, precio_unitario) 
SELECT pedido_id, material_id, 1, 100 FROM detalle_pedido LIMIT 1; -- ❌ Error esperado (UNIQUE)
```

- [ ] CHECKs en Stock funcionan
- [ ] CHECKs en Material funcionan
- [ ] CHECKs en Vehiculo funcionan
- [ ] CHECKs en Pedido funcionan
- [ ] UNIQUE constraints en Detalles funcionan

### 3.5 Verificar Sincronización (usuario.rol ↔ usuario_rol)
```python
# En Django shell: python manage.py shell
from apps.usuarios.models import Usuario, UsuarioRol

usuario = Usuario.objects.first()
print(f"usuario.rol = {usuario.rol}")
print(f"usuario_roles = {usuario.usuario_roles.all()}")

# Cambiar rol manualmente
usuario.rol = "admin"
usuario.save()

# Verificar que usuario_rol se sincronizó
print(f"usuario_roles después de cambio = {usuario.usuario_roles.all()}")  # Debería tener "admin"
```

- [ ] usuario.rol sincroniza a usuario_rol al cambiar
- [ ] usuario_roles contiene los roles esperados

---

## FASE 4: TESTS DE COMPATIBILIDAD (Código existente)

### 4.1 Vistas que usan user.rol
```python
# Ejecutar en Django shell o en tests
from apps.usuarios.models import Usuario
usuario = Usuario.objects.first()

# Verificar que user.rol aún funciona:
print(usuario.rol)  # ✓ Debería retornar valor

# Verificar que propiedades funcionan:
print(usuario.es_admin)      # ✓
print(usuario.es_conductor)  # ✓
print(usuario.es_cliente)    # ✓
print(usuario.es_empleado)   # ✓
```

- [ ] `usuario.rol` retorna valor
- [ ] Propiedades `es_admin`, `es_conductor`, etc. funcionan
- [ ] Código legado sigue funcionando

### 4.2 Acceso a Cliente en Factura
```python
# En Django shell:
from apps.facturacion.models import Factura

factura = Factura.objects.first()

# Verificar que factura.cliente funciona:
print(factura.cliente)      # ✓ Debería retornar usuario
print(factura.cliente_id)   # ✓ Debería retornar ID (propiedad)
print(factura.pedido.cliente)  # ✓ Acceso directo
```

- [ ] `factura.cliente` retorna valor correcto
- [ ] `factura.cliente_id` funciona como propiedad
- [ ] No hay errores de acceso

### 4.3 Acceso a Conductor en Pedido
```python
# En Django shell:
from apps.ordenes.models import Pedido

pedido = Pedido.objects.filter(conductor__isnull=False).first()

# Verificar acceso:
print(pedido.conductor)         # ✓ Retorna Conductor instance
print(pedido.conductor.usuario) # ✓ Acceso a Usuario
print(pedido.conductor_usuario) # ✓ Propiedad helper
```

- [ ] `pedido.conductor` retorna Conductor
- [ ] `pedido.conductor.usuario` funciona
- [ ] Propiedad `conductor_usuario` funciona

---

## FASE 5: APLICACIÓN EN NEON (BD Producción)

### 5.1 Pre-aplicación
- [ ] Último backup de Neon hecho
- [ ] Connection string guardado en lugar seguro
- [ ] Cambiar contraseña de Neon (recomendado después de producción)
- [ ] Configurar `.env` con credenciales Neon

### 5.2 Aplicar Migraciones
```bash
# EN ORDEN ESPECÍFICO:
python manage.py migrate usuarios 0003
python manage.py migrate usuarios 0004
python manage.py migrate usuarios 0005
python manage.py migrate ordenes 0002
python manage.py migrate facturacion 0002
python manage.py migrate compras 0002
```

- [ ] Migración 0003 aplicada sin errores
- [ ] Migración 0004 aplicada sin errores
- [ ] Migración 0005 aplicada sin errores
- [ ] Migración ordenes 0002 aplicada sin errores
- [ ] Migración facturacion 0002 aplicada sin errores
- [ ] Migración compras 0002 aplicada sin errores

### 5.3 Verificación Post-aplicación
```sql
-- En Neon (mismo que en local):
SELECT COUNT(*) FROM rol;
SELECT COUNT(*) FROM usuario_rol;
SELECT COUNT(*) FROM factura WHERE pedido_id IS NULL;
SELECT COUNT(*) FROM pedido WHERE conductor_id IS NOT NULL;
```

- [ ] Tablas existen y tienen datos
- [ ] Estructura es correcta
- [ ] Integridad referencial OK

### 5.4 Monitoreo Inicial (Primeras 24h)
- [ ] Revisar logs de Django (sin errores)
- [ ] Revisar logs de Neon (sin errores)
- [ ] Probar crear pedido (transacción completa)
- [ ] Probar crear factura (acceso a cliente vía pedido)
- [ ] Probar crear compra (stock se actualiza)
- [ ] Probar cambiar rol usuario (sincroniza a usuario_rol)

- [ ] Aplicación funciona sin errores
- [ ] Transacciones se completan correctamente
- [ ] Base de datos íntegra

---

## FASE 6: CAMBIO DE CONTRASEÑA NEON (SEGURIDAD)

⚠️ **IMPORTANTE**: Ya compartiste URL de conexión, debes cambiar contraseña.

```bash
# En Neon Console (o CLI):
# 1. Ir a Database Settings
# 2. Reset Password
# 3. Actualizar .env con nueva contraseña
# 4. Reiniciar aplicación
```

- [ ] Contraseña Neon cambiada
- [ ] `.env` actualizado con nueva contraseña
- [ ] Aplicación reiniciada y conectando correctamente

---

## FASE 7: DOCUMENTACIÓN Y COMIT

### 7.1 Comit en Git
```bash
git add .
git commit -m "feat: Normalización BD - 3FN implementation

- Crear tablas Rol y UsuarioRol
- Normalizar Factura (eliminar cliente_id)
- Cambiar FK de Conductor a Conductor (no Usuario)
- Agregar 16 CHECK constraints para integridad
- Sincronizar usuario.rol ↔ usuario_rol
- Sincronizar nombres ↔ first_name/last_name

Ref: #issue-id
"
git push
```

- [ ] Cambios commiteados en Git
- [ ] Mensaje de commit descriptivo
- [ ] Push a repositorio exitoso

### 7.2 Actualizar Documentación
- [ ] MER.drawio actualizado (reflejar nuevas tablas)
- [ ] README.md actualizado con nota sobre versión
- [ ] CHANGELOG.md actualizado

- [ ] MER actualizado
- [ ] Documentación refleja cambios
- [ ] README tiene notas sobre versión

---

## FASE 8: COMUNICACIÓN (Si aplica)

- [ ] ✓ Revisar que el nuevo sistema de roles es compatible
- [ ] ✓ Documentar cambios en API si es aplicable
- [ ] ✓ Comunicar a equipo sobre breaking changes (si los hay)
- [ ] ✓ Guardar documentación en lugar accesible

---

## ⚡ RESUMEN RÁPIDO

| Fase | Paso | Status |
|------|------|--------|
| 1️⃣ | Preparación | `[ ]` |
| 2️⃣ | Pruebas Locales | `[ ]` |
| 3️⃣ | Tests Datos | `[ ]` |
| 4️⃣ | Tests Compatibilidad | `[ ]` |
| 5️⃣ | Aplicar en Neon | `[ ]` |
| 6️⃣ | Cambiar Contraseña | `[ ]` |
| 7️⃣ | Documentación | `[ ]` |
| 8️⃣ | Comunicación | `[ ]` |

---

## 🆘 SI ALGO FALLA

### Rollback Rápido
```bash
# Si algo falla, revertir últimas migraciones:
python manage.py migrate usuarios 0002  # Volver a 0002
python manage.py migrate ordenes 0001   # Volver a 0001
python manage.py migrate facturacion 0001  # Volver a 0001
python manage.py migrate compras 0001   # Volver a 0001

# Restaurar BD del backup:
pg_restore -h <host> -U <user> -d database backup_20250727.dump
```

- [ ] Backup verificado y accesible
- [ ] Comando de rollback guardado
- [ ] Plan B documentado

---

## ✅ FINALIZACIÓN

- [ ] Todas las fases completadas
- [ ] Todas las verificaciones pasadas
- [ ] Sistema estable en producción
- [ ] Documentación actualizada
- [ ] Equipo notificado

---

**ÉXITO** 🎉 Tu base de datos está normalizada y lista para escalar.

Fecha de inicio: 2025-07-27
Fecha de implementación: ___________

