from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.historial.utils import registrar_actividad
from apps.usuarios.models import Proveedor
from apps.usuarios.views import admin_required

from .forms import CompraForm, DetalleCompraFormSet
from .models import Compra


def _descripcion_proveedor_desde_post(request):
    descripcion = (request.POST.get("descripcion") or "").strip()
    contacto_nombre = (request.POST.get("contacto_nombre") or "").strip()
    direccion = (request.POST.get("direccion") or "").strip()
    categoria = (request.POST.get("categoria") or "").strip()

    extras = []
    if contacto_nombre:
        extras.append(f"Contacto: {contacto_nombre}")
    if direccion:
        extras.append(f"Dirección: {direccion}")
    if categoria:
        extras.append(f"Categoría: {categoria}")

    extras_txt = "\n".join(extras)

    if descripcion and extras_txt:
        return f"{descripcion}\n{extras_txt}"
    return descripcion or extras_txt


@admin_required
def lista_compras(request):
    q = request.GET.get("q", "").strip()
    compras = (
        Compra.objects.select_related("proveedor", "usuario").prefetch_related("detalles").all()
    )

    if q:
        filtros = Q(proveedor__nombre_empresa__icontains=q) | Q(estado__icontains=q)
        if q.isdigit():
            filtros |= Q(id_compra=int(q))
        compras = compras.filter(filtros)

    return render(request, "compras/lista.html", {"compras": compras, "query": q})


@admin_required
def crear_compra(request):
    if request.method == "POST":
        form = CompraForm(request.POST)
        formset = DetalleCompraFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            compra = form.save(commit=False)
            compra.usuario = request.user
            compra.save()

            formset.instance = compra
            formset.save()
            compra.calcular_total()

            registrar_actividad(
                request,
                "crear",
                "compras",
                compra.pk,
                f"Orden de compra creada: {compra.numero_orden}",
            )
            messages.success(request, f"Orden de compra {compra.numero_orden} creada con éxito.")
            return redirect("compras:detalle_compra", id=compra.pk)

        messages.error(request, "Error al crear la orden de compra. Revisa los datos.")
    else:
        form = CompraForm()
        formset = DetalleCompraFormSet()

    return render(
        request, "compras/form.html", {"form": form, "formset": formset, "action": "Nueva"}
    )


@admin_required
def detalle_compra(request, id):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor").prefetch_related("detalles__material"), pk=id
    )
    return render(request, "compras/detalle.html", {"compra": compra})


@admin_required
def cambiar_estado_compra(request, id):
    if request.method == "POST":
        compra = get_object_or_404(Compra, pk=id)
        nuevo_estado = request.POST.get("estado")

        if nuevo_estado in dict(Compra.ESTADOS):
            compra.estado = nuevo_estado
            compra.save()
            registrar_actividad(
                request,
                "editar",
                "compras",
                compra.pk,
                f"Estado de compra {compra.numero_orden} cambiado a {nuevo_estado}",
            )
            messages.success(request, f"Estado actualizado a {nuevo_estado}.")

        return redirect("compras:detalle_compra", id=compra.pk)

    return redirect("compras:lista_compras")


@admin_required
def editar_compra(request, id):
    compra = get_object_or_404(Compra, pk=id)

    if compra.estado != "pendiente":
        messages.error(request, "Solo se pueden editar órdenes en estado pendiente.")
        return redirect("compras:detalle_compra", id=compra.pk)

    if request.method == "POST":
        form = CompraForm(request.POST, instance=compra)
        formset = DetalleCompraFormSet(request.POST, instance=compra)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            compra.calcular_total()
            messages.success(request, "Orden de compra actualizada.")
            return redirect("compras:detalle_compra", id=compra.pk)
    else:
        form = CompraForm(instance=compra)
        formset = DetalleCompraFormSet(instance=compra)

    return render(
        request,
        "compras/form.html",
        {"form": form, "formset": formset, "compra": compra, "action": "Editar"},
    )


@admin_required
def contactar_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)

    if request.method == "POST":
        asunto = request.POST.get("asunto")
        mensaje_texto = request.POST.get("mensaje")

        try:
            cuerpo_mensaje = (
                f"Mensaje de {request.user.get_full_name()} "
                f"({request.user.email}):\n\n{mensaje_texto}"
            )
            send_mail(
                asunto,
                cuerpo_mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [proveedor.correo],
                fail_silently=False,
            )
            registrar_actividad(
                request,
                "otro",
                "proveedores",
                proveedor.nit,
                f"Mensaje enviado a proveedor: {proveedor.nombre_empresa}",
            )
            messages.success(request, f"Mensaje enviado a {proveedor.nombre_empresa} con éxito.")
        except Exception:
            registrar_actividad(
                request,
                "otro",
                "proveedores",
                proveedor.nit,
                f"Intento de mensaje a {proveedor.nombre_empresa} (falló envío real)",
            )
            messages.info(request, f"Se ha registrado el mensaje para {proveedor.nombre_empresa}.")

        return redirect("compras:lista_proveedores")

    return render(request, "compras/proveedor_contacto.html", {"proveedor": proveedor})


@admin_required
def lista_proveedores(request):
    q = request.GET.get("q", "").strip()

    if q:
        proveedores = Proveedor.objects.filter(
            Q(nombre_empresa__icontains=q)
            | Q(nit__icontains=q)
            | Q(telefono__icontains=q)
            | Q(correo__icontains=q)
            | Q(descripcion__icontains=q)
        )
    else:
        proveedores = Proveedor.objects.all()

    return render(
        request, "compras/proveedores_lista.html", {"proveedores": proveedores, "query": q}
    )


@admin_required
def crear_proveedor(request):
    if request.method == "POST":
        nombre_empresa = (request.POST.get("nombre_empresa") or "").strip()
        nit = (request.POST.get("nit") or "").strip()
        telefono = (request.POST.get("telefono") or "").strip()
        correo = (request.POST.get("email") or request.POST.get("correo") or "").strip()

        proveedor = Proveedor.objects.create(
            nombre_empresa=nombre_empresa,
            nit=nit,
            telefono=telefono,
            correo=correo,
            descripcion=_descripcion_proveedor_desde_post(request),
        )

        registrar_actividad(
            request,
            "crear",
            "proveedores",
            proveedor.nit,
            f"Proveedor creado: {proveedor.nombre_empresa}",
        )
        messages.success(request, "Proveedor registrado con éxito.")
        return redirect("compras:lista_proveedores")

    return render(request, "compras/proveedor_form.html", {"action": "Crear"})


@admin_required
def editar_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)

    if request.method == "POST":
        proveedor.nombre_empresa = (request.POST.get("nombre_empresa") or "").strip()
        proveedor.nit = (request.POST.get("nit") or "").strip()
        proveedor.telefono = (request.POST.get("telefono") or "").strip()
        proveedor.correo = (request.POST.get("email") or request.POST.get("correo") or "").strip()
        proveedor.descripcion = _descripcion_proveedor_desde_post(request)
        proveedor.save()

        registrar_actividad(
            request,
            "editar",
            "proveedores",
            proveedor.nit,
            f"Proveedor editado: {proveedor.nombre_empresa}",
        )
        messages.success(request, "Proveedor actualizado.")
        return redirect("compras:lista_proveedores")

    return render(
        request, "compras/proveedor_form.html", {"proveedor": proveedor, "action": "Editar"}
    )
