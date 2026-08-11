from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from historial.utils import registrar_actividad
from usuarios.views import admin_required

from .forms import CompraForm, DetalleCompraFormSet, ProveedorMaterialFormSet, ProveedorPerfilForm
from .models import Compra, DetalleCompra, Proveedor, ProveedorMaterial


@admin_required
def lista_compras(request):
    query = request.GET.get("q", "")
    orden = request.GET.get("orden", "")
    proveedor = request.GET.get("proveedor", "")
    fecha = request.GET.get("fecha", "")
    usuario = request.GET.get("usuario", "")
    estado = request.GET.get("estado", "")

    compras = Compra.objects.select_related("proveedor", "usuario").prefetch_related("detalles")

    if query:
        compras = compras.filter(
            Q(id_compra__icontains=query)
            | Q(proveedor__nombre_empresa__icontains=query)
            | Q(proveedor__nit__icontains=query)
            | Q(estado__icontains=query)
        )

    if orden:
        compras = compras.filter(id_compra__icontains=orden)
    if proveedor:
        compras = compras.filter(
            Q(proveedor__nombre_empresa__icontains=proveedor)
            | Q(proveedor__nit__icontains=proveedor)
        )
    if fecha:
        compras = compras.filter(fecha_compra__date=fecha)
    if usuario:
        compras = compras.filter(
            Q(usuario__username__icontains=usuario)
            | Q(usuario__nombres__icontains=usuario)
            | Q(usuario__apellidos__icontains=usuario)
        )
    if estado:
        compras = compras.filter(estado=estado)

    return render(
        request,
        "compras/lista.html",
        {
            "compras": compras,
            "query": query,
            "orden": orden,
            "proveedor": proveedor,
            "fecha": fecha,
            "usuario": usuario,
            "estado_actual": estado,
        },
    )


def _detalles_desde_post(request, proveedor):
    total_forms = int(request.POST.get("detalles-TOTAL_FORMS", 0) or 0)
    detalles = []
    errores = []

    for index in range(total_forms):
        if request.POST.get(f"detalles-{index}-DELETE"):
            continue

        material_id = request.POST.get(f"detalles-{index}-material")
        cantidad_raw = request.POST.get(f"detalles-{index}-cantidad")

        if not material_id and not cantidad_raw:
            continue

        try:
            cantidad = int(cantidad_raw or 0)
        except ValueError:
            errores.append("La cantidad debe ser un número entero.")
            continue

        if cantidad <= 0:
            errores.append("La cantidad debe ser mayor a cero.")
            continue

        oferta = (
            ProveedorMaterial.objects.filter(
                proveedor=proveedor,
                material_id=material_id,
                activo=True,
            )
            .select_related("material")
            .first()
        )

        if not oferta:
            errores.append("Uno de los materiales no pertenece al catálogo activo del proveedor.")
            continue

        detalles.append((oferta.material, cantidad, oferta.precio_actual))

    if not detalles:
        errores.append("Agrega al menos un material del catálogo del proveedor.")

    return detalles, errores


@admin_required
def crear_compra(request):
    if request.method == "POST":
        form = CompraForm(request.POST)

        if form.is_valid():
            proveedor = form.cleaned_data["proveedor"]
            detalles, errores = _detalles_desde_post(request, proveedor)

            if not errores:
                with transaction.atomic():
                    compra = form.save(commit=False)
                    compra.usuario = request.user
                    compra.save()

                    for material, cantidad, precio in detalles:
                        DetalleCompra.objects.create(
                            compra=compra,
                            material=material,
                            cantidad=cantidad,
                            precio_unitario=precio,
                        )

                    compra.calcular_total()

                registrar_actividad(
                    request,
                    "crear",
                    "compras",
                    compra.id_compra,
                    f"Orden de compra creada: {compra.numero_orden}",
                )
                messages.success(request, f"Orden de compra {compra.numero_orden} creada con éxito.")
                return redirect("compras:detalle_compra", id=compra.id_compra)

            for error in errores:
                messages.error(request, error)
        else:
            messages.error(request, "Error al crear la orden de compra. Revisa los datos.")
    else:
        form = CompraForm(initial={"proveedor": request.GET.get("proveedor")})

    return render(
        request,
        "compras/form.html",
        {
            "form": form,
            "formset": DetalleCompraFormSet(),
            "action": "Nueva",
            "iva_rate": 0,
        },
    )


@admin_required
def detalle_compra(request, id):
    compra = get_object_or_404(
        Compra.objects.select_related("proveedor").prefetch_related("detalles__material"),
        id_compra=id,
    )
    return render(request, "compras/detalle.html", {"compra": compra})


@admin_required
def cambiar_estado_compra(request, id):
    if request.method == "POST":
        compra = get_object_or_404(Compra, id_compra=id)
        nuevo_estado = request.POST.get("estado")
        if nuevo_estado in dict(Compra.ESTADOS):
            compra.estado = nuevo_estado
            compra.save(update_fields=["estado"])
            registrar_actividad(
                request,
                "editar",
                "compras",
                compra.id_compra,
                f"Estado de compra {compra.numero_orden} cambiado a {nuevo_estado}",
            )
            messages.success(request, f"Estado actualizado a {nuevo_estado}.")
        return redirect("compras:detalle_compra", id=compra.id_compra)
    return redirect("compras:lista_compras")


@admin_required
def editar_compra(request, id):
    compra = get_object_or_404(Compra, id_compra=id)
    if compra.estado != "pendiente":
        messages.error(request, "Solo se pueden editar órdenes en estado pendiente.")
        return redirect("compras:detalle_compra", id=compra.id_compra)

    if request.method == "POST":
        form = CompraForm(request.POST, instance=compra)
        if form.is_valid():
            proveedor = form.cleaned_data["proveedor"]
            detalles, errores = _detalles_desde_post(request, proveedor)
            if not errores:
                with transaction.atomic():
                    form.save()
                    compra.detalles.all().delete()
                    for material, cantidad, precio in detalles:
                        DetalleCompra.objects.create(
                            compra=compra,
                            material=material,
                            cantidad=cantidad,
                            precio_unitario=precio,
                        )
                    compra.calcular_total()
                messages.success(request, "Orden de compra actualizada.")
                return redirect("compras:detalle_compra", id=compra.id_compra)
            for error in errores:
                messages.error(request, error)
    else:
        form = CompraForm(instance=compra)

    return render(
        request,
        "compras/form.html",
        {
            "form": form,
            "formset": DetalleCompraFormSet(instance=compra),
            "compra": compra,
            "action": "Editar",
            "iva_rate": 0,
        },
    )


@admin_required
def contactar_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)
    if request.method == "POST":
        asunto = request.POST.get("asunto")
        mensaje_texto = request.POST.get("mensaje")

        try:
            cuerpo_mensaje = (
                f"Mensaje de {request.user.get_full_name()} ({request.user.email}):\n\n"
                f"{mensaje_texto}"
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
                f"Intento de mensaje a {proveedor.nombre_empresa}",
            )
            messages.info(request, f"Se registró el mensaje para {proveedor.nombre_empresa}.")

        return redirect("compras:perfil_proveedor", codigo_proveedor=proveedor.codigo_proveedor)

    return render(request, "compras/proveedor_contacto.html", {"proveedor": proveedor})


@admin_required
def lista_proveedores(request):
    query = request.GET.get("q", "")
    nombre = request.GET.get("nombre", "")
    nit = request.GET.get("nit", "")
    contacto = request.GET.get("contacto", "")
    ciudad = request.GET.get("ciudad", "")
    estado = request.GET.get("estado", "")
    categoria = request.GET.get("categoria", "")

    proveedores = Proveedor.objects.prefetch_related("materiales_ofertados").all()

    if query:
        proveedores = proveedores.filter(
            Q(nombre_empresa__icontains=query)
            | Q(nit__icontains=query)
            | Q(contacto_nombre__icontains=query)
            | Q(correo__icontains=query)
            | Q(telefono__icontains=query)
        )
    if nombre:
        proveedores = proveedores.filter(nombre_empresa__icontains=nombre)
    if nit:
        proveedores = proveedores.filter(nit__icontains=nit)
    if contacto:
        proveedores = proveedores.filter(
            Q(contacto_nombre__icontains=contacto)
            | Q(correo__icontains=contacto)
            | Q(telefono__icontains=contacto)
        )
    if ciudad:
        proveedores = proveedores.filter(ciudad__icontains=ciudad)
    if estado == "activo":
        proveedores = proveedores.filter(activo=True)
    elif estado == "inactivo":
        proveedores = proveedores.filter(activo=False)
    if categoria:
        proveedores = proveedores.filter(categoria__icontains=categoria)

    filter_fields = [
        {"type": "text", "name": "nombre", "placeholder": "Nombre / empresa", "value": nombre, "size": "2"},
        {"type": "text", "name": "nit", "placeholder": "NIT / DNI", "value": nit, "size": "2"},
        {"type": "text", "name": "contacto", "placeholder": "Contacto", "value": contacto, "size": "2"},
        {"type": "text", "name": "ciudad", "placeholder": "Ciudad", "value": ciudad, "size": "2"},
        {"type": "text", "name": "categoria", "placeholder": "Categoría", "value": categoria, "size": "2"},
        {
            "type": "select",
            "name": "estado",
            "placeholder": "Estado (Todos)",
            "value": estado,
            "size": "2",
            "options": [
                {"value": "activo", "label": "Activos", "selected": estado == "activo"},
                {"value": "inactivo", "label": "Inactivos", "selected": estado == "inactivo"},
            ],
        },
    ]

    return render(
        request,
        "compras/proveedores_lista.html",
        {
            "proveedores": proveedores,
            "query": query,
            "nombre": nombre,
            "nit": nit,
            "contacto": contacto,
            "ciudad": ciudad,
            "estado_actual": estado,
            "categoria": categoria,
            "filter_fields": filter_fields,
        },
    )


@admin_required
def crear_proveedor(request):
    if request.method == "POST":
        nombre_empresa = request.POST.get("nombre_empresa")
        nit = request.POST.get("nit")
        proveedor = Proveedor.objects.create(
            nombre_empresa=nombre_empresa,
            nit=nit,
            contacto_nombre=request.POST.get("contacto_nombre"),
            telefono=request.POST.get("telefono"),
            correo=request.POST.get("email"),
            direccion=request.POST.get("direccion"),
            ciudad=request.POST.get("ciudad"),
            categoria=request.POST.get("categoria"),
            descripcion=request.POST.get("descripcion", ""),
            activo=bool(request.POST.get("activo", "on")),
        )
        registrar_actividad(
            request, "crear", "proveedores", nit, f"Proveedor creado: {nombre_empresa}"
        )
        messages.success(request, "Proveedor registrado con éxito.")
        return redirect("compras:perfil_proveedor", codigo_proveedor=proveedor.codigo_proveedor)

    return render(request, "compras/proveedor_form.html", {"action": "Crear"})


@admin_required
def editar_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)
    if request.method == "POST":
        proveedor.nombre_empresa = request.POST.get("nombre_empresa")
        proveedor.nit = request.POST.get("nit")
        proveedor.contacto_nombre = request.POST.get("contacto_nombre")
        proveedor.telefono = request.POST.get("telefono")
        proveedor.correo = request.POST.get("email")
        proveedor.direccion = request.POST.get("direccion")
        proveedor.ciudad = request.POST.get("ciudad")
        proveedor.categoria = request.POST.get("categoria")
        proveedor.descripcion = request.POST.get("descripcion", "")
        proveedor.activo = bool(request.POST.get("activo"))
        proveedor.save()

        registrar_actividad(
            request,
            "editar",
            "proveedores",
            proveedor.nit,
            f"Proveedor editado: {proveedor.nombre_empresa}",
        )
        messages.success(request, "Proveedor actualizado.")
        return redirect("compras:perfil_proveedor", codigo_proveedor=proveedor.codigo_proveedor)

    return render(
        request,
        "compras/proveedor_form.html",
        {"proveedor": proveedor, "action": "Editar"},
    )


@admin_required
def perfil_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(
        Proveedor.objects.prefetch_related("materiales_ofertados__material__unidad_medida"),
        codigo_proveedor=codigo_proveedor,
    )

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

    catalogo = proveedor.materiales_ofertados.select_related("material", "material__unidad_medida")

    return render(
        request,
        "compras/proveedor_perfil.html",
        {
            "proveedor": proveedor,
            "form": form,
            "formset": formset,
            "catalogo": catalogo,
        },
    )


@admin_required
@require_POST
def cambiar_estado_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)
    proveedor.activo = not proveedor.activo
    proveedor.save(update_fields=["activo"])
    estado = "habilitado" if proveedor.activo else "inhabilitado"
    registrar_actividad(
        request,
        "editar",
        "proveedores",
        proveedor.nit,
        f"Proveedor {estado}: {proveedor.nombre_empresa}",
    )
    messages.success(request, f"Proveedor {estado} correctamente.")
    return redirect(request.POST.get("next") or reverse("compras:lista_proveedores"))


@admin_required
def materiales_proveedor_json(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor, activo=True)
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
            "precio": str(item.precio_actual),
            "fecha_actualizacion": item.fecha_actualizacion.strftime("%d/%m/%Y %H:%M"),
            "disponible": item.activo,
            "referencia": item.referencia_proveedor,
        }
        for item in materiales
    ]

    return JsonResponse(
        {
            "proveedor": {
                "id": proveedor.codigo_proveedor,
                "nombre": proveedor.nombre_empresa,
                "contacto": proveedor.contacto_nombre,
            },
            "materiales": data,
        }
    )
