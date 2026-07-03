"""
Endpoints JSON (autocompletar, select2, AJAX).
"""

from html import escape
from django.http import JsonResponse
from django.urls import reverse

from usuarios.models import Material, Catalogo
from usuarios.views import admin_required

from core.datatables import get_dt_params, apply_search, build_dt_response


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


@admin_required
def api_materiales_listado(request):
    params = get_dt_params(request)
    tipo = request.GET.get("tipo", "").strip()

    qs = Material.objects.select_related("stock_info", "catalogo", "unidad_medida").all()
    total = qs.count()

    qs = apply_search(qs, params["search"], ["nombre", "descripcion"])

    if tipo:
        qs = qs.filter(catalogo__codigo_catalogo=tipo)

    filtrados = qs.count()
    materiales = qs.order_by("nombre")[params["start"]: params["start"] + params["length"]]

    data = []
    for material in materiales:
        nombre_seguro = escape(material.nombre)
        data.append(
            {
                "id": material.id,
                "material": nombre_seguro,
                "tipo": material.tipo or "-",
                "unidad": getattr(material.unidad_medida, "abreviatura", "-"),
                "stock": getattr(getattr(material, "stock_info", None), "cantidad_actual", 0),
                "precio": f"${material.precio_referencia:,.0f}".replace(",", "."),
                "acciones": f'''
                    <div class="d-flex justify-content-center gap-2">
                        <a href="{reverse('inventario:editar_material', args=[material.id])}" class="btn-action" title="Editar">
                            <i class="bi bi-pencil"></i>
                        </a>
                        <a href="{reverse('inventario:eliminar_material', args=[material.id])}" class="btn-action btn-action--danger confirm-delete" title="Eliminar"
                           data-title="¿Eliminar material?" data-text="¿Estás seguro de que deseas eliminar {nombre_seguro}?">
                            <i class="bi bi-trash"></i>
                        </a>
                    </div>
                ''',
            }
        )

    return build_dt_response(params["draw"], total, filtrados, data)
