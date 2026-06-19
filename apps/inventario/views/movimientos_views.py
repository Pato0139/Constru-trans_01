"""
Vistas del Kardex (movimientos de entrada/salida).
"""
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from apps.usuarios.models import Material
from apps.usuarios.views import admin_required

from ..models import MovimientoInventario
from ..services import KardexService


@admin_required
@require_POST
def registrar_entrada(request):
    material_id = request.POST.get('material_id')
    try:
        cantidad = int(request.POST.get('cantidad', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Cantidad inválida'}, status=400)

    if cantidad <= 0:
        return JsonResponse({'error': 'Cantidad debe ser > 0'}, status=400)

    try:
        movimiento = KardexService.registrar_movimiento(
            material_id=material_id,
            tipo='entrada',
            cantidad=cantidad,
            observacion=request.POST.get('motivo', 'entrada manual'),
            usuario=request.user,
        )
        return JsonResponse({'status': 'ok', 'stock': movimiento.material.stock_info.cantidad_actual})
    except Material.DoesNotExist:
        return JsonResponse({'error': 'Material no existe'}, status=404)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)


@admin_required
def movimientos_lista(request):
    query = request.GET.get('q')
    tipo = request.GET.get('tipo')

    movimientos = MovimientoInventario.objects.all().select_related('material', 'usuario')

    if query:
        movimientos = movimientos.filter(
            Q(material__nombre__icontains=query) |
            Q(observacion__icontains=query)
        )

    if tipo:
        movimientos = movimientos.filter(tipo_movimiento=tipo)

    materiales = Material.objects.all().order_by('nombre')
    return render(request, "inventario/movimientos.html", {
        "movimientos": movimientos,
        "materiales": materiales,
        "query": query,
        "tipo_actual": tipo,
    })
