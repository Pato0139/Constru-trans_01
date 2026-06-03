# Fase 6 — Evidencia de revisión de cálculos

## Metodología

1. Revisión del modelo `DetallePedido.subtotal` y `Pedido.calcular_total()`.
2. Revisión del JavaScript en `apps/clientes/templates/clientes/form.html`.
3. Ejecución del script automatizado:

```powershell
python scripts/verificar_calculos_pedido.py
```

## Resultados (casos del instructor)

| Caso | Cantidad | Precio unitario | Cálculo esperado | Cálculo backend (Decimal) | Formato UI (JS) | Resultado |
|------|----------|-----------------|------------------|---------------------------|-----------------|-----------|
| Pedido 1 | 3 | 2850 | 8550 | 8550 | $8.550,00 | ✅ Correcto |
| Pedido 2 | 5 | 1000 | 5000 | 5000 | $5.000,00 | ✅ Correcto |
| Pedido 3 | 2 | 3499 | 6998 | 6998 | $6.998,00 | ✅ Correcto |

## Hallazgos técnicos

| ID | Hallazgo | Tipo | Acción aplicada |
|----|----------|------|-----------------|
| C1 | Acumulación JS con `parseFloat` sin redondear | Funcional potencial | `Math.round(x * 100) / 100` al sumar/restar líneas |
| C2 | Vista `crear_pedido` usa `material.precio` (= `precio_referencia`) | — | Coherente con catálogo |
| C3 | No hay IVA ni transporte en el total del pedido | Diseño | Documentar en informe: total = suma de líneas únicamente |

## Cómo verificar en la aplicación (prueba manual)

1. Iniciar sesión como cliente.
2. Crear pedido: 3 unidades de un material con precio **2850**.
3. Comparar «Total estimado» en pantalla con detalle guardado en «Mis pedidos».
4. Repetir con cantidades 5×1000 y 2×3499.

Registrar en [02-plantilla-prueba-usabilidad.md](02-plantilla-prueba-usabilidad.md) § Prueba de cálculos.
