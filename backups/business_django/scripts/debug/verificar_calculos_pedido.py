#!/usr/bin/env python
"""
Fase 6 — Verificación de cálculos de pedido (sin base de datos).
Ejecutar: python scripts/verificar_calculos_pedido.py
"""

from decimal import Decimal


def subtotal(cantidad: int, precio_unitario) -> Decimal:
    return Decimal(cantidad) * Decimal(str(precio_unitario))


def format_currency_js(value: float) -> str:
    """Réplica de formatCurrency en clientes/form.html"""
    formatted = f"{value:,.2f}"
    res = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return "$" + res


CASOS = [
    {"nombre": "Pedido 1", "cantidad": 3, "precio": 2850, "esperado": 8550},
    {"nombre": "Pedido 2", "cantidad": 5, "precio": 1000, "esperado": 5000},
    {"nombre": "Pedido 3", "cantidad": 2, "precio": 3499, "esperado": 6998},
]


def main():
    print("=" * 60)
    print("FASE 6 — Verificación de cálculos Constru-Trans")
    print("=" * 60)
    errores = 0
    for caso in CASOS:
        calc = subtotal(caso["cantidad"], caso["precio"])
        ok = calc == Decimal(caso["esperado"])
        js_display = format_currency_js(float(calc))
        estado = "CORRECTO" if ok else "INCORRECTO"
        if not ok:
            errores += 1
        print(f"\n{caso['nombre']}: {caso['cantidad']} x {caso['precio']}")
        print(f"  Esperado:     {caso['esperado']}")
        print(f"  Calculado:  {calc}")
        print(f"  UI (JS fmt): {js_display}")
        print(f"  Resultado:   {estado}")

    print("\n" + "-" * 60)
    print("Notas técnicas:")
    print("- Backend: DetallePedido.subtotal = cantidad * precio_unitario")
    print("- Pedido.calcular_total(): suma de subtotales")
    print("- Riesgo UI: parseFloat + acumulación JS puede diferir en decimales largos")
    print("-" * 60)
    if errores:
        print(f"FALLO: {errores} caso(s) con error en lógica Decimal")
        return 1
    print("OK: Lógica de subtotal alineada con casos del instructor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
