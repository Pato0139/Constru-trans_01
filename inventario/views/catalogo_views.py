"""
Vistas del Catálogo (tipos de material).
"""

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from historial.utils import registrar_actividad
from usuarios.forms import CatalogoForm, UnidadMedidaForm
from usuarios.models import Catalogo, UnidadMedida
from usuarios.views import admin_required


@admin_required
def tipos_material_lista(request):
    query = request.GET.get("q")
    tipos = Catalogo.objects.annotate(num_materiales=Count("materiales"))

    if query:
        tipos = tipos.filter(
            Q(codigo_catalogo__icontains=query) | Q(nombre_empresa__icontains=query)
        )

    tipos = tipos.order_by("codigo_catalogo")

    context = {
        "tipos": tipos,
        "query": query,
    }

    return render(request, "inventario/tipos_lista.html", context)


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
    context = {"form": form, "action": "crear"}

    return render(request, "inventario/form_tipo.html", context)


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
    context = {"form": form, "action": "editar", "tipo": tipo}

    return render(request, "inventario/form_tipo.html", context)


@admin_required
def eliminar_tipo_material(request, codigo):
    tipo = get_object_or_404(Catalogo, pk=codigo)

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


@admin_required
def unidades_medida_lista(request):
    query = request.GET.get("q")
    unidades = UnidadMedida.objects.annotate(num_materiales=Count("materiales"))

    if query:
        unidades = unidades.filter(
            Q(codigo__icontains=query)
            | Q(nombre__icontains=query)
            | Q(abreviatura__icontains=query)
        )

    unidades = unidades.order_by("orden", "nombre")

    context = {
        "unidades": unidades,
        "query": query,
    }
    return render(request, "inventario/unidades_lista.html", context)


@admin_required
def crear_unidad_medida(request):
    if request.method == "POST":
        form = UnidadMedidaForm(request.POST)
        if form.is_valid():
            try:
                unidad = form.save()
                registrar_actividad(
                    request,
                    "crear",
                    "unidad_medida",
                    unidad.pk,
                    f"Unidad de medida creada: {unidad.nombre}",
                )
                messages.success(request, "Unidad de medida creada correctamente.")
                return redirect("inventario:unidades_medida_lista")
            except Exception as e:
                messages.error(request, f"Error al crear unidad de medida: {e}")
    else:
        form = UnidadMedidaForm()
    context = {"form": form, "action": "crear"}
    return render(request, "inventario/form_unidad.html", context)


@admin_required
def editar_unidad_medida(request, id):
    unidad = get_object_or_404(UnidadMedida, pk=id)
    if request.method == "POST":
        form = UnidadMedidaForm(request.POST, instance=unidad)
        if form.is_valid():
            unidad = form.save()
            registrar_actividad(
                request,
                "editar",
                "unidad_medida",
                unidad.pk,
                f"Unidad de medida editada: {unidad.nombre}",
            )
            messages.success(request, "Unidad de medida actualizada correctamente.")
            return redirect("inventario:unidades_medida_lista")
    else:
        form = UnidadMedidaForm(instance=unidad)
    context = {"form": form, "action": "editar", "unidad": unidad}
    return render(request, "inventario/form_unidad.html", context)


@admin_required
def eliminar_unidad_medida(request, id):
    unidad = get_object_or_404(UnidadMedida, pk=id)

    if unidad.materiales.exists():
        messages.error(
            request,
            f"No se puede eliminar '{unidad.nombre}' porque tiene materiales asociados.",
        )
        return redirect("inventario:unidades_medida_lista")

    nombre = unidad.nombre
    unidad.delete()
    registrar_actividad(
        request, "eliminar", "unidad_medida", id, f"Unidad de medida eliminada: {nombre}")
    messages.success(request, f"Unidad de medida '{nombre}' eliminada correctamente.")
    return redirect("inventario:unidades_medida_lista")
