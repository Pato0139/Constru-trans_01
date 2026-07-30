"""
Endpoints JSON (autocompletar, select2, AJAX).
"""

from html import escape
from django.http import JsonResponse
from django.middleware.csrf import get_token
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
    material_query = request.GET.get("material", "").strip()
    id_query = request.GET.get("id", "").strip()

    qs = Material.objects.select_related("stock_info", "catalogo", "unidad_medida").all()
    total = qs.count()

    qs = apply_search(qs, params["search"], ["nombre", "descripcion"])

    if tipo:
        qs = qs.filter(catalogo__codigo_catalogo=tipo)
    if material_query:
        qs = qs.filter(nombre__icontains=material_query)
    if id_query:
        qs = qs.filter(id__icontains=id_query)

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
                "acciones": f'''
                    <div class="d-flex justify-content-center gap-2">
                        <a href="{reverse('inventario:editar_material', args=[material.id])}" class="btn-action" title="Editar">
                            <i class="bi bi-pencil"></i>
                        </a>
                        <form method="post" action="{reverse('inventario:cambiar_estado_material', args=[material.id])}" class="d-inline">
                            <input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">
                            <button type="submit" class="btn-action {'btn-action--danger' if material.activo else 'btn-action--success'}"
                                    title="{'Inhabilitar' if material.activo else 'Habilitar'} material"
                                    aria-label="{'Inhabilitar' if material.activo else 'Habilitar'} {nombre_seguro}">
                                <i class="bi {'bi-toggle-on' if material.activo else 'bi-toggle-off'}"></i>
                            </button>
                        </form>
                    </div>
                ''',
            }
        )

    return build_dt_response(params["draw"], total, filtrados, data)
