"""
Endpoints JSON (autocompletar, select2, AJAX).
"""

from django.http import JsonResponse

from apps.usuarios.models import Material
from apps.usuarios.views import admin_required


@admin_required
def api_materiales(request):
    materiales = Material.objects.filter(stock_info__cantidad_actual__gt=0).select_related(
        "stock_info"
    )
    data = []
    for m in materiales:
        data.append(
            {
                "id": m.pk,
                "nombre": m.nombre,
                "precio": float(getattr(m, "precio_referencia", 0)),
                "stock": m.stock_info.cantidad_actual if hasattr(m, "stock_info") else 0,
                "tipo": getattr(m, "tipo", ""),
            }
        )
    return JsonResponse(data, safe=False)
