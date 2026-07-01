# Plan de Pruebas Unitarias

## Objetivo
Cada módulo principal tiene su propia suite de tests en una carpeta `tests/` por app, con pruebas reales (no placeholders) para modelos, vistas y formularios.

---

## Estructura de Tests
Cada app con tests tiene la siguiente estructura:
```
app/
├── tests/
│   ├── __init__.py
│   ├── test_models.py          # Pruebas de modelos, métodos y properties
│   ├── test_views.py           # Pruebas de vistas, templates y status codes
│   ├── test_forms.py           # Pruebas de formularios y validaciones
│   └── test_permissions.py     # Pruebas de permisos y autenticación (si aplica)
```

---

## Tests Implementados

### usuarios/tests/
| Archivo | Pruebas Implementadas |
|---------|-----------------------|
| `test_models.py` | `test_crear_usuario_normal()`, `test_usuario_tiene_iniciales()`, `test_crear_conductor()`, `test_crear_vehiculo()`, `test_asignar_vehiculo()` |
| `test_views.py` | `test_login_y_permisos_admin()`, `test_asignar_vehiculo_a_conductor()`, `test_lista_conductores_muestra_datos()` |

---

## Tests Faltantes (Prioridad Alta)

### usuarios/tests/test_forms.py
- `test_registro_valido()`: Prueba de formulario de registro válido
- `test_registro_correo_duplicado()`: Prueba de error por correo duplicado
- `test_registro_documento_duplicado()`: Prueba de error por documento duplicado
- `test_registro_contrasenas_no_coinciden()`: Prueba de error por contraseñas que no coinciden
- `test_registro_documento_invalido()`: Prueba de documento con longitud incorrecta

### inventario/tests/test_models.py
- `test_crear_unidad_medida()`: Prueba de creación de unidad de medida
- `test_crear_material()`: Prueba de creación de material
- `test_crear_stock()`: Prueba de creación de stock

### inventario/tests/test_stock.py
- `test_stock_actualizado()`: Prueba de actualización de stock (si aplica)
- `test_stock_negativo_prohibido()`: Prueba de que stock no puede ser negativo

### compras/tests/test_models.py
- `test_crear_proveedor()`: Prueba de creación de proveedor
- `test_crear_compra()`: Prueba de creación de compra
- `test_total_compra_calculado()`: Prueba de cálculo de total de compra

### ordenes/tests/test_models.py
- `test_crear_pedido()`: Prueba de creación de pedido
- `test_detalle_pedido_calcula_total()`: Prueba de que detalle actualiza total del pedido
- `test_crear_entrega()`: Prueba de creación de entrega

### facturacion/tests/test_models.py
- `test_crear_factura()`: Prueba de creación de factura
- `test_total_pagado_calculado()`: Prueba de cálculo de total pagado
- `test_factura_se_marca_como_pagada()`: Prueba de que estado se actualiza a pagada

---

## Ejecutar Pruebas
```bash
# Todas las pruebas
pytest

# Coverage report
pytest --cov=usuarios --cov=clientes --cov=inventario --cov=compras --cov=ordenes --cov=gestion_pedidos --cov=facturacion --cov=pagos --cov=ia

# Solo una app
pytest usuarios/tests/
```

---

## Coverage Objetivo
> 70% mínimo en módulos críticos (usuarios, inventario, pedidos, facturacion)
