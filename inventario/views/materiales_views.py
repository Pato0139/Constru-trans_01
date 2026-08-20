"""
Vistas de Materiales (CRUD) y Stock.
"""

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from historial.utils import registrar_actividad
from usuarios.forms import MaterialForm
from usuarios.models import Catalogo, Material, Stock
from usuarios.views import admin_required


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
        {
            "name": "id",
            "type": "text",
            "placeholder": "ID",
            "value": material_id,
        },
        {
            "name": "material",
            "type": "text",
            "placeholder": "Material",
            "value": material,
        },
        {
            "name": "tipo",
            "type": "select",
            "placeholder": "Todos los tipos",
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

    return render(request, "inventario/lista.html", context)


@admin_required
def crear_material(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            try:
                material = form.save()
                Stock.objects.get_or_create(
                    material=material,
                    defaults={"cantidad_actual": 0, "stock_minimo": 10},
                )
                registrar_actividad(
                    request,
                    "crear",
                    "inventario",
                    material.pk,
                    f"Material creado: {material.nombre}",
                )

                success_msg = "Material creado correctamente."
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"status": "success", "message": success_msg})
                messages.success(request, success_msg)
                return redirect("inventario:materiales_lista")
            except Exception as e:
                error_msg = f"Error al crear material: {e}"
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"status": "error", "message": error_msg}, status=500)
                messages.error(request, error_msg)
    else:
        form = MaterialForm()
    context = {"form": form, "action": "crear"}

    return render(request, "inventario/form.html", context)


@admin_required
def editar_material(request, id):
    material = get_object_or_404(Material, pk=id)
    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            registrar_actividad(
                request, "editar", "inventario", material.pk, f"Material editado: {material.nombre}"
            )
            messages.success(request, "Material actualizado correctamente.")
            return redirect("inventario:materiales_lista")
    else:
        form = MaterialForm(instance=material)
    context = {"form": form, "action": "editar"}

    return render(request, "inventario/form.html", context)


@admin_required
def eliminar_material(request, id):
    material = get_object_or_404(Material, pk=id)

    stock_actual = getattr(getattr(material, "stock_info", None), "cantidad_actual", 0)
    if stock_actual > 0:
        messages.error(
            request,
            f"No se puede eliminar {material.nombre} porque aún tiene stock ({stock_actual}).",
        )
        return redirect("inventario:materiales_lista")

    if material.detallepedido_set.exists():
        messages.error(
            request, f"No se puede eliminar {material.nombre}: está en pedidos existentes."
        )
        return redirect("inventario:materiales_lista")

    nombre = material.nombre
    material.delete()
    registrar_actividad(request, "eliminar", "inventario", id, f"Material eliminado: {nombre}")
    messages.success(request, f"Material {nombre} eliminado correctamente.")
    return redirect("inventario:materiales_lista")


@admin_required
def cambiar_estado_material(request, id):
    """Cambia la disponibilidad sin borrar el material ni su historial."""
    if request.method != "POST":
        messages.error(request, "La actualización del estado requiere una solicitud POST.")
        return redirect("inventario:materiales_lista")

    material = get_object_or_404(Material, pk=id)
    material.activo = not material.activo
    material.save(update_fields=["activo"])
    estado = "habilitado" if material.activo else "inhabilitado"
    registrar_actividad(request, "actualizar", "inventario", material.pk, f"Material {estado}: {material.nombre}")
    messages.success(request, f"Material {material.nombre} {estado} correctamente.")
    return redirect("inventario:materiales_lista")


@admin_required
def stock_lista(request):
    material = request.GET.get("material", "")
    ubicacion = request.GET.get("ubicacion", "")
    stock_actual = request.GET.get("stock_actual", "")
    q = request.GET.get("q", "")

    stocks = Stock.objects.all().select_related("material")

    if material:
        stocks = stocks.filter(material__nombre__icontains=material)
    if ubicacion:
        stocks = stocks.filter(ubicacion__icontains=ubicacion)
    if stock_actual and stock_actual.isdigit():
        stocks = stocks.filter(cantidad_actual=int(stock_actual))
    if q:
        stocks = stocks.filter(
            Q(material__nombre__icontains=q) | Q(ubicacion__icontains=q)
        )

    filter_fields = [
        {"type": "text", "name": "material", "placeholder": "Material", "value": material},
        {"type": "text", "name": "ubicacion", "placeholder": "Ubicación", "value": ubicacion},
        {"type": "text", "name": "stock_actual", "placeholder": "Stock exacto", "value": stock_actual},
    ]

    context = {
        "stocks": stocks,
        "material": material,
        "ubicacion": ubicacion,
        "stock_actual": stock_actual,
        "q": q,
        "filter_fields": filter_fields,
    }

    return render(request, "inventario/stock.html", context)


@admin_required
def editar_stock(request, id):
    stock = get_object_or_404(Stock, material_id=id)
    if request.method == "POST":
        try:
            cantidad = int(request.POST.get("cantidad", "0"))
        except (ValueError, TypeError):
            messages.error(request, "La cantidad debe ser un número válido.")
            return redirect("inventario:stock_lista")
        stock.cantidad_actual = cantidad
        stock.ubicacion = request.POST.get("ubicacion", "")
        stock.save()
        messages.success(request, f"Stock de {stock.material.nombre} actualizado.")
        return redirect("inventario:stock_lista")
    context = {"stock": stock}

    return render(request, "inventario/form_stock.html", context)


def buscar_materiales(query=None):
    """Helper para autocompletar — se mantiene por compatibilidad."""
    if not query:
        return Material.objects.none()
    return Material.objects.filter(nombre__icontains=query)[:20]



