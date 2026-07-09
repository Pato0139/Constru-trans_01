from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from historial.utils import registrar_actividad
from usuarios.views import admin_required

from .forms import CompraForm, DetalleCompraFormSet, ProveedorPerfilForm, ProveedorMaterialFormSet
from .models import Compra, Proveedor, ProveedorMaterial


@admin_required
def lista_compras(request):
    orden = request.GET.get("orden", "")
    proveedor = request.GET.get("proveedor", "")
    fecha = request.GET.get("fecha", "")
    usuario = request.GET.get("usuario", "")
    estado = request.GET.get("estado", "")

    compras = (
        Compra.objects.select_related("proveedor", "usuario").prefetch_related("detalles").all()
    )

    if orden:
        compras = compras.filter(id_compra__icontains=orden)
    if proveedor:
        compras = compras.filter(
            Q(proveedor__nombre_empresa__icontains=proveedor) | Q(proveedor__nit__icontains=proveedor)
        )
    if fecha:
        compras = compras.filter(fecha_compra__date=fecha)
    if usuario:
        compras = compras.filter(
            Q(usuario__username__icontains=usuario) |
            Q(usuario__nombres__icontains=usuario) |
            Q(usuario__apellidos__icontains=usuario)
        )
    if estado:
        compras = compras.filter(estado=estado)

    context = {
        "compras": compras,
        "orden": orden,
        "proveedor": proveedor,
        "fecha": fecha,
        "usuario": usuario,
        "estado_actual": estado,
    }

    return render(request, "compras/lista.html", context)


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

            # Recalcular total por si es necesario
            compra.calcular_total()

            registrar_actividad(
                request,
                "crear",
                "compras",
                compra.id,
                f"Orden de compra creada: {compra.numero_orden}",
            )
            messages.success(request, f"Orden de compra {compra.numero_orden} creada con éxito.")
            return redirect("compras:detalle_compra", id=compra.id)
        else:
            messages.error(request, "Error al crear la orden de compra. Revisa los datos.")
    else:
        form = CompraForm()
        formset = DetalleCompraFormSet()

    context = {"form": form, "formset": formset, "action": "Nueva"}

    return render(request, "compras/form.html", context)


@admin_required
def detalle_compra(request, id):
    # Optimizacion
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor").prefetch_related("detalles__material"), id=id
    )
    context = {"compra": compra}

    return render(request, "compras/detalle.html", context)


@admin_required
def cambiar_estado_compra(request, id):
    if request.method == "POST":
        compra = get_object_or_404(Compra, id=id)
        nuevo_estado = request.POST.get("estado")
        if nuevo_estado in dict(Compra.ESTADOS):
            compra.estado = nuevo_estado
            compra.save()
            registrar_actividad(
                request,
                "editar",
                "compras",
                compra.id,
                f"Estado de compra {compra.numero_orden} cambiado a {nuevo_estado}",
            )
            messages.success(request, f"Estado actualizado a {nuevo_estado}.")
        return redirect("compras:detalle_compra", id=compra.id)
    return redirect("compras:lista_compras")


@admin_required
def editar_compra(request, id):
    compra = get_object_or_404(Compra, id=id)
    if compra.estado != "pendiente":
        messages.error(request, "Solo se pueden editar órdenes en estado pendiente.")
        return redirect("compras:detalle_compra", id=compra.id)

    if request.method == "POST":
        form = CompraForm(request.POST, instance=compra)
        formset = DetalleCompraFormSet(request.POST, instance=compra)

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            compra.calcular_total()
            messages.success(request, "Orden de compra actualizada.")
            return redirect("compras:detalle_compra", id=compra.id)
    else:
        form = CompraForm(instance=compra)
        formset = DetalleCompraFormSet(instance=compra)

    context = {"form": form, "formset": formset, "compra": compra, "action": "Editar"}

    return render(request, "compras/form.html", context)


@admin_required
def contactar_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)
    if request.method == "POST":
        asunto = request.POST.get("asunto")
        mensaje_texto = request.POST.get("mensaje")

        try:
            cuerpo_mensaje = f"Mensaje de {request.user.get_full_name()} ({request.user.email}):\n\n{mensaje_texto}"
            send_mail(
                asunto,
                cuerpo_mensaje,
                settings.DEFAULT_FROM_EMAIL,
                [proveedor.email],
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
                f"Intento de mensaje a {proveedor.nombre_empresa} (Falló envío real)",
            )
            messages.info(
                request,
                f"Se ha registrado el mensaje para {proveedor.nombre_empresa} (Simulación de envío).",
            )

        return redirect("compras:lista_proveedores")

    context = {"proveedor": proveedor}

    return render(request, "compras/proveedor_contacto.html", context)


@admin_required
def lista_proveedores(request):
    empresa_nit = request.GET.get("empresa_nit", "")
    contacto = request.GET.get("contacto", "")
    categoria = request.GET.get("categoria", "")

    proveedores = Proveedor.objects.all()

    if empresa_nit:
        proveedores = proveedores.filter(
            Q(nombre_empresa__icontains=empresa_nit) | Q(nit__icontains=empresa_nit)
        )
    if contacto:
        proveedores = proveedores.filter(
            Q(contacto_nombre__icontains=contacto) | Q(email__icontains=contacto) | Q(telefono__icontains=contacto)
        )
    if categoria:
        proveedores = proveedores.filter(categoria__icontains=categoria)

    context = {
        "proveedores": proveedores,
        "empresa_nit": empresa_nit,
        "contacto": contacto,
        "categoria": categoria,
    }

    return render(request, "compras/proveedores_lista.html", context)


@admin_required
def crear_proveedor(request):
    if request.method == "POST":
        nombre_empresa = request.POST.get("nombre_empresa")
        nit = request.POST.get("nit")
        contacto_nombre = request.POST.get("contacto_nombre")
        telefono = request.POST.get("telefono")
        email = request.POST.get("email")
        direccion = request.POST.get("direccion")
        categoria = request.POST.get("categoria")

        Proveedor.objects.create(
            nombre_empresa=nombre_empresa,
            nit=nit,
            contacto_nombre=contacto_nombre,
            telefono=telefono,
            email=email,
            direccion=direccion,
            categoria=categoria,
        )
        registrar_actividad(
            request, "crear", "proveedores", nit, f"Proveedor creado: {nombre_empresa}"
        )
        messages.success(request, "Proveedor registrado con éxito.")
        return redirect("compras:lista_proveedores")

    context = {"action": "Crear"}

    return render(request, "compras/proveedor_form.html", context)


@admin_required
def editar_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)
    if request.method == "POST":
        proveedor.nombre_empresa = request.POST.get("nombre_empresa")
        proveedor.nit = request.POST.get("nit")
        proveedor.contacto_nombre = request.POST.get("contacto_nombre")
        proveedor.telefono = request.POST.get("telefono")
        proveedor.email = request.POST.get("email")
        proveedor.direccion = request.POST.get("direccion")
        proveedor.categoria = request.POST.get("categoria")
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

    context = {"proveedor": proveedor, "action": "Editar"}

    return render(request, "compras/proveedor_form.html", context)


@admin_required
def perfil_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)

    if request.method == "POST":
        form = ProveedorPerfilForm(request.POST, instance=proveedor)
        formset = ProveedorMaterialFormSet(request.POST, instance=proveedor, prefix="catalogo")
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, "Perfil del proveedor actualizado correctamente.")
            return redirect("compras:perfil_proveedor", codigo_proveedor=proveedor.codigo_proveedor)
    else:
        form = ProveedorPerfilForm(instance=proveedor)
        formset = ProveedorMaterialFormSet(instance=proveedor, prefix="catalogo")

    return render(request, "compras/proveedor_perfil.html", {
        "proveedor": proveedor,
        "form": form,
        "formset": formset,
    })


@admin_required
def materiales_proveedor_json(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)
    materiales = (
        ProveedorMaterial.objects.filter(proveedor=proveedor, activo=True)
        .select_related("material", "material__unidad_medida")
        .order_by("material__nombre")
    )

    data = [
        {
            "id": item.material_id,
            "nombre": item.material.nombre,
            "unidad": getattr(item.material.unidad_medida, "abreviatura", ""),
            "precio": str(item.precio_proveedor),
            "referencia": item.referencia_proveedor,
        }
        for item in materiales
    ]

    return JsonResponse({
        "proveedor": {
            "id": proveedor.codigo_proveedor,
            "nombre": proveedor.nombre_empresa,
            "contacto": proveedor.contacto_nombre,
        },
        "materiales": data,
    })
