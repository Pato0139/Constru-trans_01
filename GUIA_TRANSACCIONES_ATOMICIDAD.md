# Atomicidad en Aplicación - Transacciones de Negocio

## Objetivo
Garantizar que operaciones de negocio complejas (crear pedido, registrar compra, etc.) sean atómicas: o se completan totalmente o se revierten completamente (ROLLBACK).

---

## 1. OPERACIONES CRÍTICAS PARA TRANSACCIONES

### 1.1 Crear Pedido Completo
**Contexto**: Cuando un cliente crea un pedido con detalles y descuentos, todo debe validarse junto.

**Flujo Actual (RIESGO)**:
```python
# ❌ MAL - Sin transacción
pedido = Pedido.objects.create(usuario=user, cliente=cliente, total=0)
for detalle_data in detalles:
    DetallePedido.objects.create(pedido=pedido, material=material, cantidad=qty)
    # Si falla aquí, pedido queda vacío

# Si el siguiente falla:
if ejecutar_validaciones():  # Y esto falla
    # Pedido ya existe pero sin detalles ❌
```

**Flujo Mejorado (CORRECTO)**:
```python
from django.db import transaction

@transaction.atomic
def crear_pedido_completo(usuario, cliente, detalles):
    """Crear pedido con detalles en una sola transacción."""
    try:
        # Crear pedido
        pedido = Pedido.objects.create(
            usuario=usuario,
            cliente=cliente,
            total=0,
            estado='pendiente'
        )
        
        # Crear detalles
        total = 0
        for detalle_data in detalles:
            material = MaterialConstruccion.objects.get(cod_material=detalle_data['material_id'])
            cantidad = detalle_data['cantidad']
            
            # Validar stock disponible
            stock = Stock.objects.select_for_update().get(material=material)
            if stock.cantidad_actual < cantidad:
                raise ValueError(f"Stock insuficiente para {material.nombre}")
            
            # Crear detalle
            precio_unitario = detalle_data.get('precio_unitario', material.precio_referencia)
            DetallePedido.objects.create(
                pedido=pedido,
                material=material,
                cantidad=cantidad,
                precio_unitario=precio_unitario
            )
            total += cantidad * precio_unitario
        
        # Actualizar total
        pedido.total = total
        pedido.save()
        
        return pedido
        
    except Exception as e:
        # Transacción se revierte automáticamente
        raise
```

---

### 1.2 Registrar Compra + Actualizar Stock
**Contexto**: Cuando se registra una compra, el stock debe actualizarse atómicamente.

```python
from django.db import transaction

@transaction.atomic
def registrar_compra_y_actualizar_stock(proveedor, detalles):
    """Registrar compra y actualizar stock en una transacción."""
    try:
        # Crear compra
        compra = Compra.objects.create(
            proveedor=proveedor,
            total_compra=0,
            estado='recibida'
        )
        
        total = 0
        movimientos = []
        
        for detalle_data in detalles:
            material = MaterialConstruccion.objects.get(cod_material=detalle_data['material_id'])
            cantidad = detalle_data['cantidad']
            precio_unitario = detalle_data['precio_unitario']
            
            # 1. Crear detalle de compra
            DetalleCompra.objects.create(
                compra=compra,
                material=material,
                cantidad=cantidad,
                precio_unitario=precio_unitario
            )
            total += cantidad * precio_unitario
            
            # 2. Actualizar stock (usar SELECT FOR UPDATE para bloqueo)
            stock = Stock.objects.select_for_update().get(material=material)
            stock.cantidad_actual += cantidad
            stock.save()
            
            # 3. Registrar movimiento de inventario (si existe tabla)
            movimientos.append({
                'material': material,
                'cantidad': cantidad,
                'tipo': 'entrada'
            })
        
        # 4. Actualizar total de compra
        compra.total_compra = total
        compra.save()
        
        return compra
        
    except Exception as e:
        # Todo se revierte: compra, detalles, stock
        raise
```

---

### 1.3 Facturar Pedido + Confirmar Stock
**Contexto**: Al facturar, confirmar que el stock fue descontado o descontarlo ahora.

```python
from django.db import transaction

@transaction.atomic
def facturar_pedido(pedido, subtotal, iva_rate=0.19):
    """Crear factura y descontar stock de pedido."""
    try:
        # 1. Validar que hay stock para todos los detalles
        for detalle in pedido.detalles.all():
            stock = Stock.objects.select_for_update().get(material=detalle.material)
            if stock.cantidad_actual < detalle.cantidad:
                raise ValueError(f"Stock insuficiente para {detalle.material.nombre}")
        
        # 2. Descontar stock
        for detalle in pedido.detalles.all():
            stock = Stock.objects.select_for_update().get(material=detalle.material)
            stock.cantidad_actual -= detalle.cantidad
            if stock.cantidad_actual < 0:
                raise ValueError("Stock negativo - violación de restricción")
            stock.save()
        
        # 3. Crear factura
        iva = Decimal(subtotal) * Decimal(iva_rate)
        total = Decimal(subtotal) + iva
        
        factura = Factura.objects.create(
            pedido=pedido,
            numero=generar_numero_factura(),  # Implementar función
            subtotal=subtotal,
            iva=iva,
            total=total,
            estado='pendiente'
        )
        
        # 4. Cambiar estado de pedido
        pedido.estado = 'en_ruta'  # O el estado correspondiente
        pedido.save()
        
        return factura
        
    except Exception as e:
        # Todo se revierte: descuentos de stock, factura, cambios de estado
        raise
```

---

### 1.4 Registrar Pago + Cambiar Estado Factura
**Contexto**: Un pago debe atualizar estado de factura transaccionalmente.

```python
from django.db import transaction
from decimal import Decimal

@transaction.atomic
def registrar_pago_factura(factura, monto, metodo_pago, usuario):
    """Registrar pago y actualizar estado de factura."""
    try:
        # 1. Obtener factura con bloqueo
        factura = Factura.objects.select_for_update().get(id_factura=factura.id_factura)
        
        # Validar estado
        if factura.estado == 'anulada':
            raise ValueError("No se puede pagar factura anulada")
        
        # Validar monto
        saldo_pendiente = factura.saldo_pendiente
        if monto <= 0:
            raise ValueError("Monto debe ser positivo")
        if monto > saldo_pendiente:
            raise ValueError(f"Monto excede saldo pendiente: ${saldo_pendiente}")
        
        # 2. Crear pago
        pago = Pago.objects.create(
            factura=factura,
            monto=monto,
            codigo_metodo_pago=metodo_pago,
            registrado_por=usuario
        )
        
        # 3. Actualizar estado de factura si está pagada
        nuevo_saldo = factura.saldo_pendiente
        if nuevo_saldo <= 0:
            factura.estado = 'pagada'
            factura.save()
        
        return pago
        
    except Exception as e:
        # Todo se revierte: pago y cambios de estado
        raise
```

---

## 2. PATRÓN: Transacciones en Vistas

### Template para Vistas

```python
from django.db import transaction
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

@transaction.atomic
def crear_pedido_view(request):
    """Vista con transacción completa."""
    try:
        # 1. Validar datos de entrada
        datos = json.loads(request.body)
        usuario = request.user
        cliente = Cliente.objects.get(id=datos['cliente_id'])
        detalles = datos['detalles']
        
        # 2. Crear pedido en transacción
        pedido = crear_pedido_completo(usuario, cliente, detalles)
        
        # 3. Retornar resultado
        return JsonResponse({
            'status': 'success',
            'pedido_id': pedido.codigo_pedido,
            'total': str(pedido.total)
        })
        
    except ValueError as e:
        # Transacción se revierte, retornar error
        logger.warning(f"Error en validación: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
        
    except Exception as e:
        # Transacción se revierte, log de error
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': 'Error en la operación'
        }, status=500)
```

---

## 3. BLOQUEO PESIMISTA: SELECT FOR UPDATE

### Problema
En concurrencia alta, dos transacciones podrían leer el mismo stock, decrementarlo en paralelo y causar inconsistencia.

**Antes (INSEGURO)**:
```python
stock = Stock.objects.get(material=material)  # ❌ Sin bloqueo
# Otro proceso podría modificar stock aquí
stock.cantidad_actual -= cantidad
stock.save()
```

**Después (SEGURO)**:
```python
stock = Stock.objects.select_for_update().get(material=material)  # ✓ Con bloqueo
# Otros procesos esperan hasta que termines
stock.cantidad_actual -= cantidad
stock.save()
```

---

## 4. CONFIGURACIÓN EN DJANGO

### settings.py

```python
# Transacciones automáticas por vista
ATOMIC_REQUESTS = False  # Mantener False, usar @transaction.atomic en vistas críticas

# Para PostgreSQL, usar REPEATABLE READ aislamiento
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'isolation_level': psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ,
        },
    }
}
```

---

## 5. TESTING DE TRANSACCIONES

### Ejemplo de Test

```python
from django.test import TestCase, TransactionTestCase
from django.db import transaction

class PedidoTransactionTest(TransactionTestCase):
    """Usar TransactionTestCase para tests con transacciones reales."""
    
    def test_crear_pedido_con_stock_insuficiente(self):
        """Verificar que transacción se revierte si falta stock."""
        # Setup
        usuario = Usuario.objects.create(username='test')
        material = MaterialConstruccion.objects.create(...)
        stock = Stock.objects.create(material=material, cantidad_actual=5)
        
        # Intentar crear pedido con más cantidad que stock
        with self.assertRaises(ValueError):
            crear_pedido_completo(
                usuario=usuario,
                cliente=None,
                detalles=[{'material_id': material.id, 'cantidad': 10}]
            )
        
        # Verificar que no se creó ningún pedido (transacción se revirtió)
        self.assertEqual(Pedido.objects.count(), 0)
    
    def test_crear_pedido_exitoso(self):
        """Verificar que transacción se completa correctamente."""
        # Setup
        usuario = Usuario.objects.create(username='test')
        material = MaterialConstruccion.objects.create(...)
        stock = Stock.objects.create(material=material, cantidad_actual=100)
        
        # Crear pedido
        pedido = crear_pedido_completo(
            usuario=usuario,
            cliente=None,
            detalles=[{'material_id': material.id, 'cantidad': 10}]
        )
        
        # Verificar
        self.assertIsNotNone(pedido)
        self.assertEqual(pedido.total, 10 * material.precio_referencia)
        self.assertEqual(pedido.detalles.count(), 1)
```

---

## 6. RESUMEN: Checklist de Atomicidad

- ✅ `@transaction.atomic` en todas las vistas de negocio complejo
- ✅ `select_for_update()` para stock y inventario
- ✅ Validaciones de negocio dentro de la transacción
- ✅ CHECKs en BD como defensa adicional
- ✅ Tests con `TransactionTestCase`
- ✅ Logging de errores y rollbacks
- ✅ Manejo de excepciones apropiado

---

## 7. RECOMENDACIÓN FINAL

Implementar estas transacciones de negocio **después** de aplicar las migraciones de normalización. Las CHECKs en BD más las transacciones en aplicación garantizarán atomicidad, consistencia e integridad completas.

