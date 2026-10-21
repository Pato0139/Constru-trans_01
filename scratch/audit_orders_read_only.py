import os
import sys

sys.path.insert(0, os.getcwd())
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from decimal import Decimal
from apps.pedidos.models import Pedido, DetallePedido
from apps.catalogo.models import MaterialConstruccion, HistorialPrecioMaterial
from apps.pagos.models import Factura

print("=" * 80, flush=True)
print("AUDITORÍA DE SOLO LECTURA: 89 PEDIDOS Y DETALLES", flush=True)
print("=" * 80, flush=True)

# Cargar en memoria todos los pedidos con detalles y materiales
pedidos = list(Pedido.objects.all().select_related('usuario', 'cliente').prefetch_related('detalles__material').order_by('-fecha_solicitud'))
total_pedidos = len(pedidos)
print(f"Total pedidos cargados: {total_pedidos}\n", flush=True)

# Pre-cargar todo el catálogo e historiales de precios
materiales_dict = {m.id: m for m in MaterialConstruccion.objects.all()}
historiales_list = list(HistorialPrecioMaterial.objects.all().order_by('-fecha_cambio'))

inconsistencias_total = []
detalles_precio_distinto = []
detalles_sin_coincidencia_historial = []

for p in pedidos:
    detalles = list(p.detalles.all())
    suma_detalles = sum((d.subtotal for d in detalles), Decimal("0.00"))
    descuento = p.descuento or Decimal("0.00")
    total_esperado = max(suma_detalles - descuento, Decimal("0.00"))
    
    if abs(p.total - total_esperado) > Decimal("0.01"):
        inconsistencias_total.append({
            "codigo_pedido": p.codigo_pedido,
            "total_guardado": p.total,
            "suma_detalles": suma_detalles,
            "descuento": descuento,
            "total_esperado": total_esperado,
            "diferencia": p.total - total_esperado,
            "creador": str(p.usuario),
            "fecha": str(p.fecha_solicitud)[:19],
        })

    for d in detalles:
        mat_id = d.material_id
        mat = materiales_dict.get(mat_id)
        if not mat:
            detalles_sin_coincidencia_historial.append({
                "pedido_id": p.codigo_pedido,
                "material_id": mat_id,
                "material_nombre": "[MATERIAL HUÉRFANO/ELIMINADO]",
                "precio_detalle": d.precio_unitario,
                "precio_catalogo_actual": Decimal("0.00"),
                "precio_historial_fecha": None,
                "coincide": False,
                "fecha_pedido": str(p.fecha_solicitud)[:19]
            })
            continue

        if abs(d.precio_unitario - mat.precio) > Decimal("0.01"):
            # Buscar en lista de historiales pre-cargada
            precio_historial = None
            for h in historiales_list:
                if h.material_id == mat_id and h.fecha_cambio <= p.fecha_solicitud:
                    precio_historial = h.precio_nuevo
                    break
            
            coincide = (precio_historial is not None and abs(d.precio_unitario - precio_historial) <= Decimal("0.01"))
            det_info = {
                "pedido_id": p.codigo_pedido,
                "material_id": mat.id,
                "material_nombre": mat.nombre,
                "precio_detalle": d.precio_unitario,
                "precio_catalogo_actual": mat.precio,
                "precio_historial_fecha": precio_historial,
                "coincide": coincide,
                "fecha_pedido": str(p.fecha_solicitud)[:19]
            }
            detalles_precio_distinto.append(det_info)
            if not coincide:
                detalles_sin_coincidencia_historial.append(det_info)

print(f"1. Pedidos con total inconsistente con sus detalles: {len(inconsistencias_total)} de {total_pedidos}", flush=True)
for inc in inconsistencias_total[:20]:
    print(f"   Pedido #{inc['codigo_pedido']}: Total={inc['total_guardado']} | SumaDet={inc['suma_detalles']} | Desc={inc['descuento']} | Dif={inc['diferencia']} | Creador={inc['creador']} | Fecha={inc['fecha']}", flush=True)

print(f"\n2. Detalles con precio unitario distinto al catálogo actual: {len(detalles_precio_distinto)}", flush=True)
print(f"   De ellos, NO coinciden con HistorialPrecio a la fecha: {len(detalles_sin_coincidencia_historial)}", flush=True)
for d in detalles_sin_coincidencia_historial[:20]:
    print(f"   Pedido #{d['pedido_id']} - Mat #{d['material_id']} ({d['material_nombre'][:20]}): Detalle={d['precio_detalle']} | CatActual={d['precio_catalogo_actual']} | Hist={d['precio_historial_fecha']} | Fecha={d['fecha_pedido']}", flush=True)

print("\n" + "=" * 80, flush=True)
print("AUDITORÍA DE SOLO LECTURA: FACTURAS VS DETALLES DE PEDIDO", flush=True)
print("=" * 80, flush=True)
facturas = list(Factura.objects.all().select_related('pedido').order_by('id_factura'))
print(f"Total facturas analizadas: {len(facturas)}\n", flush=True)

facturas_inconsistentes = []
for f in facturas:
    pedido = f.pedido
    if pedido:
        suma_det = sum((d.subtotal for d in pedido.detalles.all()), Decimal("0.00"))
        dif = f.subtotal - suma_det
        if abs(dif) > Decimal("0.01"):
            facturas_inconsistentes.append({
                "id_factura": f.id_factura,
                "pedido_id": pedido.codigo_pedido,
                "subtotal_factura": f.subtotal,
                "suma_detalles_pedido": suma_det,
                "diferencia": dif
            })
    else:
        facturas_inconsistentes.append({
            "id_factura": f.id_factura,
            "pedido_id": "Sin pedido",
            "subtotal_factura": f.subtotal,
            "suma_detalles_pedido": Decimal("0.00"),
            "diferencia": f.subtotal
        })

print(f"Facturas cuyo subtotal no coincide con la suma de detalles de su pedido: {len(facturas_inconsistentes)}", flush=True)
for fi in facturas_inconsistentes:
    print(f"   Factura #{fi['id_factura']} (Pedido #{fi['pedido_id']}): Subtotal Factura={fi['subtotal_factura']} | Suma Detalles={fi['suma_detalles_pedido']} | Dif={fi['diferencia']}", flush=True)
