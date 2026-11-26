from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.catalogo.forms import MaterialForm
from apps.catalogo.models import Catalogo, Stock
from apps.catalogo.models import MaterialConstruccion as Material
from apps.catalogo.services.kardex import calcular_nivel_alerta_stock
from apps.usuarios.views import admin_required
from config.utils import registrar_actividad


@admin_required
def materiales_lista(request):
    material = request.GET.get("material", "").strip()
    tipo = request.GET.get("tipo", "").strip()
    material_id = request.GET.get("id", "").strip()

    tipos = Catalogo.objects.all().order_by("nombre_empresa")
    tipos_unicos = []
    vistos = set()
    for tipo_item in tipos:
        clave = (tipo_item.nombre_empresa or "").strip().lower()
        if not clave or clave in vistos:
            continue
        vistos.add(clave)
        tipos_unicos.append(tipo_item)

    total = Material.objects.count()

    filter_fields = [
        {"name": "material", "type": "text", "placeholder": "Producto", "value": material},
        {
            "name": "tipo",
            "type": "select",
            "placeholder": "Todas las categorías",
            "value": tipo,
            "options": [
                {
                    "value": t.codigo_catalogo,
                    "label": t.nombre_empresa,
                    "selected": t.codigo_catalogo == tipo,
                }
                for t in tipos_unicos
            ],
        },
    ]

    context = {
        "material": material,
        "material_id": material_id,
        "tipo_actual": tipo,
        "tipos": tipos_unicos,
        "total": total,
        "filter_fields": filter_fields,
    }

    return render(request, "catalogo/lista.html", context)


@admin_required
def crear_material(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            try:
                material = form.save()
                Stock.objects.get_or_create(
                    material=material,
                    defaults={
                        "cantidad_actual": form.cleaned_data.get("stock") or 0,
                        "stock_minimo": form.cleaned_data["stock_minimo"],
                    },
                )
                registrar_actividad(
                    request,
                    "crear",
                    "catalogo",
                    material.pk,
                    f"Material creado: {material.nombre}",
                )

                success_msg = "Material creado correctamente."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"status": "success", "message": success_msg})
                messages.success(request, success_msg)
                next_url = request.GET.get("next", "")
                if url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect("catalogo:materiales_lista")
            except Exception as e:
                error_msg = f"Error al crear material: {e}"
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"status": "error", "message": error_msg}, status=500)
                messages.error(request, error_msg)
    else:
        form = MaterialForm()
    context = {"form": form, "action": "crear"}

    return render(request, "catalogo/form.html", context)


@admin_required
def editar_material(request, id):
    material = get_object_or_404(Material, pk=id)
    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            registrar_actividad(
                request, "editar", "catalogo", material.pk, f"Material editado: {material.nombre}"
            )
            messages.success(request, "Material actualizado correctamente.")
            return redirect("catalogo:materiales_lista")
    else:
        form = MaterialForm(instance=material)
    context = {"form": form, "action": "editar"}

    return render(request, "catalogo/form.html", context)


@admin_required
@require_POST
def eliminar_material(request, id):
    material = get_object_or_404(Material, pk=id)

    stock_actual = getattr(getattr(material, "stock_info", None), "cantidad_actual", 0)
    if stock_actual > 0:
        messages.error(
            request,
            f"No se puede eliminar {material.nombre} porque aún tiene stock ({stock_actual}).",
        )
        return redirect("catalogo:materiales_lista")

    if material.detallepedido_set.exists():
        messages.error(
            request, f"No se puede eliminar {material.nombre}: está en pedidos existentes."
        )
        return redirect("catalogo:materiales_lista")

    nombre = material.nombre
    material.delete()
    registrar_actividad(request, "eliminar", "catalogo", id, f"Material eliminado: {nombre}")
    messages.success(request, f"Material {nombre} eliminado correctamente.")
    return redirect("catalogo:materiales_lista")


@admin_required
def cambiar_estado_material(request, id):
    if request.method != "POST":
        messages.error(request, "La actualización del estado requiere una solicitud POST.")
        return redirect("catalogo:materiales_lista")

    material = get_object_or_404(Material, pk=id)
    material.activo = not material.activo
    material.estado = "activo" if material.activo else "inactivo"
    material.save(update_fields=["activo", "estado"])
    estado = "habilitado" if material.activo else "inhabilitado"
    registrar_actividad(
        request, "actualizar", "catalogo", material.pk, f"Material {estado}: {material.nombre}"
    )
    messages.success(request, f"Material {material.nombre} {estado} correctamente.")
    return redirect("catalogo:materiales_lista")


@admin_required
def stock_lista(request):
    from django.db.models import F

    material = request.GET.get("material", "")
    ubicacion = request.GET.get("ubicacion", "")
    stock_actual = request.GET.get("stock_actual", "")
    estado = request.GET.get("estado", "").strip()
    q = request.GET.get("q", "")

    stocks = Stock.objects.all().select_related(
        "material", "material__unidad_medida", "material__marca", "material__catalogo"
    )

    if material:
        stocks = stocks.filter(material__nombre__icontains=material)
    if ubicacion:
        stocks = stocks.filter(ubicacion__icontains=ubicacion)
    if stock_actual and stock_actual.isdigit():
        stocks = stocks.filter(cantidad_actual=int(stock_actual))
    if estado == "disponible":
        stocks = stocks.filter(cantidad_actual__gt=F("stock_minimo"))
    elif estado == "bajo":
        stocks = stocks.filter(cantidad_actual__gt=0, cantidad_actual__lte=F("stock_minimo"))
    elif estado == "agotado":
        stocks = stocks.filter(cantidad_actual__lte=0)
    if q:
        stocks = stocks.filter(Q(material__nombre__icontains=q) | Q(ubicacion__icontains=q))

    filter_fields = [
        {"type": "text", "name": "material", "label": "Material", "placeholder": "Material", "value": material},
        {"type": "text", "name": "ubicacion", "label": "Ubicación", "placeholder": "Ubicación", "value": ubicacion},
        {
            "type": "text",
            "name": "stock_actual",
            "label": "Cantidad",
            "placeholder": "Stock exacto",
            "value": stock_actual,
        },
        {
            "type": "select",
            "name": "estado",
            "label": "Estado",
            "placeholder": "Estado (Todos)",
            "value": estado,
            "options": [
                {"value": "disponible", "label": "Disponible", "selected": estado == "disponible"},
                {"value": "bajo", "label": "Stock bajo", "selected": estado == "bajo"},
                {"value": "agotado", "label": "Agotado", "selected": estado == "agotado"},
            ],
        },
    ]

    stocks = list(stocks.order_by("material__nombre"))
    for item in stocks:
        item.nivel_alerta = calcular_nivel_alerta_stock(
            item.cantidad_actual, item.stock_minimo
        )
        item.diferencia_stock_minimo = max(0, item.stock_minimo - item.cantidad_actual)
        item.unidad_label = (
            item.material.unidad_medida.abreviatura
            or item.material.unidad_medida.nombre
            or "unidades"
        )

    conteo_alertas = list(
        Stock.objects.values_list("cantidad_actual", "stock_minimo")
    )
    total_stock_critico = sum(
        calcular_nivel_alerta_stock(actual, minimo) == "critico"
        for actual, minimo in conteo_alertas
    )
    total_stock_bajo = sum(
        calcular_nivel_alerta_stock(actual, minimo) == "bajo"
        for actual, minimo in conteo_alertas
    )

    context = {
        "stocks": stocks,
        "total_stock_critico": total_stock_critico,
        "total_stock_bajo": total_stock_bajo,
        "total_stock_alerta": total_stock_critico + total_stock_bajo,
        "material": material,
        "ubicacion": ubicacion,
        "stock_actual": stock_actual,
        "q": q,
        "filter_fields": filter_fields,
    }

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "catalogo/_stock_body.html", context)

    return render(request, "catalogo/stock.html", context)


@admin_required
def editar_stock(request, id):
    stock = get_object_or_404(Stock, material_id=id)
    if request.method == "POST":
        ubicacion = request.POST.get("ubicacion", "").strip()
        try:
            cantidad = int(request.POST.get("cantidad", ""))
            stock_minimo = int(request.POST.get("stock_minimo", ""))
        except (ValueError, TypeError):
            messages.error(request, "El stock actual y su mínimo deben ser números enteros válidos.")
            return redirect("catalogo:stock_lista")
        if not 0 <= cantidad <= 100000 or stock_minimo < 0 or len(ubicacion) > 120:
            messages.error(request, "Las cantidades no pueden ser negativas y la ubicación debe ser válida.")
            return redirect("catalogo:stock_lista")
        stock.cantidad_actual = cantidad
        stock.stock_minimo = stock_minimo
        stock.ubicacion = ubicacion
        stock.save()
        messages.success(request, f"Stock actual y mínimo de {stock.material.nombre} actualizados.")
        return redirect("catalogo:stock_lista")
    context = {"stock": stock}

    return render(request, "catalogo/form_stock.html", context)


def buscar_materiales(query=None):
    if not query:
        return Material.objects.none()
    return Material.objects.filter(nombre__icontains=query)[:20]
