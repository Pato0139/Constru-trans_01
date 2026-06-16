from django.contrib import messages
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.historial.utils import registrar_actividad
from apps.usuarios.forms import CatalogoForm, MaterialForm
from apps.usuarios.models import Catalogo, Material, Stock
from apps.usuarios.views import admin_required
from core.db_preference import debe_usar_bd_remota

from .models import MovimientoInventario


@admin_required
@require_POST
def registrar_entrada(request):
    material_id = request.POST.get("material_id")
    try:
        cantidad = int(request.POST.get("cantidad", 0))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Cantidad inválida"}, status=400)

    if cantidad <= 0:
        return JsonResponse({"error": "Cantidad debe ser > 0"}, status=400)

    try:
        db_alias = "remota" if debe_usar_bd_remota() else "default"
        with transaction.atomic(using=db_alias):
            material = Material.objects.select_for_update().using(db_alias).get(pk=material_id)
            stock, _ = (
                Stock.objects.select_for_update()
                .using(db_alias)
                .get_or_create(
                    material=material,
                    defaults={"cantidad_actual": 0},
                )
            )

            stock.cantidad_actual = F("cantidad_actual") + cantidad
            stock.save(using=db_alias)
            stock.refresh_from_db(using=db_alias)

            MovimientoInventario.objects.create(
                material=material,
                tipo_movimiento="entrada",
                cantidad=cantidad,
                observacion=request.POST.get("motivo", "entrada manual"),
                usuario=request.user,
            )
        return JsonResponse({"status": "ok", "stock": stock.cantidad_actual})
    except Material.DoesNotExist:
        return JsonResponse({"error": "Material no existe"}, status=404)


@admin_required
def movimientos_lista(request):
    query = request.GET.get("q")
    tipo = request.GET.get("tipo")

    movimientos = MovimientoInventario.objects.all().select_related("material", "usuario")

    if query:
        movimientos = movimientos.filter(
            Q(material__nombre__icontains=query) | Q(observacion__icontains=query)
        )

    if tipo:
        movimientos = movimientos.filter(tipo_movimiento=tipo)

    materiales = Material.objects.all().order_by("nombre")
    return render(
        request,
        "inventario/movimientos.html",
        {
            "movimientos": movimientos,
            "materiales": materiales,
            "query": query,
            "tipo_actual": tipo,
        },
    )


def buscar_materiales(query=None):
    materiales = Material.objects.all().select_related("stock_info")
    if query:
        materiales = materiales.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))
    return materiales


@admin_required
def stock_lista(request):
    q = request.GET.get("q")
    stocks = Stock.objects.all().select_related("material")

    if q:
        stocks = stocks.filter(Q(material__nombre__icontains=q) | Q(ubicacion__icontains=q))

    page = int(request.GET.get("page", 1))
    per_page = 25
    total = stocks.count()
    stocks = stocks[(page - 1) * per_page : page * per_page]

    return render(
        request,
        "inventario/stock.html",
        {
            "stocks": stocks,
            "query": q,
            "page": page,
            "per_page": per_page,
            "total": total,
        },
    )


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
    return render(request, "inventario/form_stock.html", {"stock": stock})


@admin_required
def materiales_lista(request):
    query = request.GET.get("q")
    tipo = request.GET.get("tipo")

    materiales = Material.objects.all().select_related("stock_info", "catalogo")

    if query:
        materiales = materiales.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query))

    if tipo:
        materiales = materiales.filter(catalogo__codigo_catalogo=tipo)

    tipos = Catalogo.objects.all().order_by("nombre_empresa")

    page = int(request.GET.get("page", 1))
    per_page = 25
    total = materiales.count()
    materiales = materiales[(page - 1) * per_page : page * per_page]

    return render(
        request,
        "inventario/lista.html",
        {
            "materiales": materiales,
            "query": query,
            "tipo_actual": tipo,
            "tipos": tipos,
            "page": page,
            "per_page": per_page,
            "total": total,
        },
    )


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
    return render(request, "inventario/form.html", {"form": form, "action": "crear"})


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
    return render(request, "inventario/form.html", {"form": form, "action": "editar"})


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


# =====================================================================
# CRUD TIPOS DE MATERIAL (CATALOGO)
# =====================================================================


@admin_required
def tipos_material_lista(request):
    query = request.GET.get("q")
    tipos = Catalogo.objects.annotate(num_materiales=Count("materiales"))

    if query:
        tipos = tipos.filter(
            Q(codigo_catalogo__icontains=query) | Q(nombre_empresa__icontains=query)
        )

    tipos = tipos.order_by("codigo_catalogo")

    return render(
        request,
        "inventario/tipos_lista.html",
        {
            "tipos": tipos,
            "query": query,
        },
    )


@admin_required
def crear_tipo_material(request):
    if request.method == "POST":
        form = CatalogoForm(request.POST)
        if form.is_valid():
            try:
                tipo = form.save()
                registrar_actividad(
                    request,
                    "crear",
                    "catalogo",
                    tipo.pk,
                    f"Tipo de material creado: {tipo.nombre_empresa}",
                )
                messages.success(request, "Tipo de material creado correctamente.")
                return redirect("inventario:tipos_material_lista")
            except Exception as e:
                messages.error(request, f"Error al crear tipo de material: {e}")
    else:
        form = CatalogoForm()
    return render(request, "inventario/form_tipo.html", {"form": form, "action": "crear"})


@admin_required
def editar_tipo_material(request, codigo):
    tipo = get_object_or_404(Catalogo, pk=codigo)
    if request.method == "POST":
        form = CatalogoForm(request.POST, instance=tipo)
        if form.is_valid():
            form.save()
            registrar_actividad(
                request,
                "editar",
                "catalogo",
                tipo.pk,
                f"Tipo de material editado: {tipo.nombre_empresa}",
            )
            messages.success(request, "Tipo de material actualizado correctamente.")
            return redirect("inventario:tipos_material_lista")
    else:
        form = CatalogoForm(instance=tipo)
    return render(
        request, "inventario/form_tipo.html", {"form": form, "action": "editar", "tipo": tipo}
    )


@admin_required
def eliminar_tipo_material(request, codigo):
    tipo = get_object_or_404(Catalogo, pk=codigo)

    # Validar integridad referencial (no eliminar si tiene materiales asociados)
    if tipo.materiales.exists():
        messages.error(
            request,
            f"No se puede eliminar '{tipo.nombre_empresa}' porque tiene materiales asociados.",
        )
        return redirect("inventario:tipos_material_lista")

    nombre = tipo.nombre_empresa
    tipo.delete()
    registrar_actividad(
        request, "eliminar", "catalogo", codigo, f"Tipo de material eliminado: {nombre}"
    )
    messages.success(request, f"Tipo de material '{nombre}' eliminado correctamente.")
    return redirect("inventario:tipos_material_lista")
