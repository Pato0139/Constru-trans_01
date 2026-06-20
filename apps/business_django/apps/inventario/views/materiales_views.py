"""
Vistas de Materiales (CRUD) y Stock.
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.historial.utils import registrar_actividad
from apps.usuarios.forms import MaterialForm
from apps.usuarios.models import Material, Stock
from apps.usuarios.views import admin_required


@admin_required
def materiales_lista(request):
    query = request.GET.get('q')
    tipo = request.GET.get('tipo')

    materiales = Material.objects.all().select_related('stock_info', 'catalogo')

    if query:
        materiales = materiales.filter(
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query)
        )

    if tipo:
        materiales = materiales.filter(catalogo__codigo_catalogo=tipo)

    tipos = Catalogo.objects.all().order_by('nombre_empresa')

    page = int(request.GET.get('page', 1))
    per_page = 25
    total = materiales.count()
    materiales = materiales[(page - 1) * per_page:page * per_page]

    context = {
        "materiales": materiales,
        "query": query,
        "tipo_actual": tipo,
        "tipos": tipos,
        "page": page,
        "per_page": per_page,
        "total": total,
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
                    defaults={'cantidad_actual': 0, 'stock_minimo': 10},
                )
                registrar_actividad(request, 'crear', 'inventario', material.pk,
                                    f"Material creado: {material.nombre}")

                success_msg = "Material creado correctamente."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"status": "success", "message": success_msg})
                messages.success(request, success_msg)
                return redirect("inventario:materiales_lista")
            except Exception as e:
                error_msg = f"Error al crear material: {e}"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
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
            registrar_actividad(request, 'editar', 'inventario', material.pk,
                                f"Material editado: {material.nombre}")
            messages.success(request, "Material actualizado correctamente.")
            return redirect("inventario:materiales_lista")
    else:
        form = MaterialForm(instance=material)
    context = {"form": form, "action": "editar"}

    return render(request, "inventario/form.html", context)


@admin_required
def eliminar_material(request, id):
    material = get_object_or_404(Material, pk=id)

    stock_actual = getattr(getattr(material, 'stock_info', None), 'cantidad_actual', 0)
    if stock_actual > 0:
        messages.error(
            request,
            f"No se puede eliminar {material.nombre} porque aún tiene stock ({stock_actual})."
        )
        return redirect("inventario:materiales_lista")

    if material.detallepedido_set.exists():
        messages.error(request,
                       f"No se puede eliminar {material.nombre}: está en pedidos existentes.")
        return redirect("inventario:materiales_lista")

    nombre = material.nombre
    material.delete()
    registrar_actividad(request, 'eliminar', 'inventario', id, f"Material eliminado: {nombre}")
    messages.success(request, f"Material {nombre} eliminado correctamente.")
    return redirect("inventario:materiales_lista")


@admin_required
def stock_lista(request):
    q = request.GET.get('q')
    stocks = Stock.objects.all().select_related('material')

    if q:
        stocks = stocks.filter(
            Q(material__nombre__icontains=q) |
            Q(ubicacion__icontains=q)
        )

    page = int(request.GET.get('page', 1))
    per_page = 25
    total = stocks.count()
    stocks = stocks[(page - 1) * per_page:page * per_page]

    context = {
        "stocks": stocks,
        "query": q,
        "page": page,
        "per_page": per_page,
        "total": total,
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


# Importar Catalogo aquí para evitar circular import
from apps.usuarios.models import Catalogo
from django.http import JsonResponse
