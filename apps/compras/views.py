from decimal import Decimal
import logging

from django.conf import settings
from django.contrib import messages

logger = logging.getLogger(__name__)
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, router, transaction
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
import uuid
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.catalogo.models import MaterialConstruccion
from apps.catalogo.services import KardexService
from apps.usuarios.views import admin_required
from config.db_utils import select_for_update_if_supported
from config.utils import registrar_actividad

from .forms import (
    EntradaCompraForm,
    EntradaDetalleCompraFormSet,
    ProveedorForm,
    ProveedorMaterialFormSet,
)
from .models import Compra, DetalleCompra, Proveedor, ProveedorMaterial


@admin_required
def lista_compras(request):
    proveedor = request.GET.get("proveedor", "").strip()
    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    factura = request.GET.get("factura", "").strip()
    material = request.GET.get("material", "").strip()

    compras = Compra.objects.select_related("proveedor", "usuario").prefetch_related(
        Prefetch(
            "detalles",
            queryset=DetalleCompra.objects.select_related("material"),
            to_attr="detalles_cargados",
        )
    )

    estado = request.GET.get("estado", "").strip()
    if proveedor:
        compras = compras.filter(proveedor__nombre_empresa__icontains=proveedor)
    if fecha_desde:
        compras = compras.filter(fecha_compra__date__gte=fecha_desde)
    if fecha_hasta:
        compras = compras.filter(fecha_compra__date__lte=fecha_hasta)
    if factura:
        compras = compras.filter(numero_factura__icontains=factura)
    if material:
        compras = compras.filter(
            Q(detalles__material_nombre__icontains=material)
            | Q(detalles__material__nombre__icontains=material)
        ).distinct()
    if estado:
        compras = compras.filter(estado=estado)

    filter_fields = [
        {
            "type": "text",
            "name": "proveedor",
            "label": "Proveedor",
            "placeholder": "Proveedor",
            "value": proveedor,
            "size": "3",
        },
        {"type": "date", "name": "fecha_desde", "label": "Desde", "placeholder": "Desde", "value": fecha_desde, "size": "2"},
        {"type": "date", "name": "fecha_hasta", "label": "Hasta", "placeholder": "Hasta", "value": fecha_hasta, "size": "2"},
        {"type": "text", "name": "factura", "label": "Factura / entrada", "placeholder": "Factura / entrada", "value": factura, "size": "2"},
        {
            "type": "text",
            "name": "material",
            "label": "Material",
            "placeholder": "Material",
            "value": material,
            "size": "3",
        },
        {
            "type": "select",
            "name": "estado",
            "label": "Estado",
            "placeholder": "Estado (Todos)",
            "value": estado,
            "size": "2",
            "options": [
                {"value": "recibida", "label": "Recibida", "selected": estado == "recibida"},
                {"value": "pendiente", "label": "Pendiente", "selected": estado == "pendiente"},
                {"value": "cancelada", "label": "Cancelada", "selected": estado == "cancelada"},
            ],
        },
    ]

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return render(
            request,
            "compras/_compras_body.html",
            {"compras": compras},
        )

    return render(
        request,
        "compras/lista.html",
        {
            "compras": compras,
            "proveedor": proveedor,
            "material": material,
            "filter_fields": filter_fields,
            "has_filters": any([proveedor, fecha_desde, fecha_hasta, factura, material, estado]),
        },
    )


@admin_required
def crear_compra(request):
    db_alias = router.db_for_write(Compra)
    proveedor_id = request.POST.get("proveedor") if request.method == "POST" else request.GET.get("proveedor")
    proveedor = Proveedor.objects.filter(pk=proveedor_id, activo=True).first() if str(proveedor_id or "").isdigit() else None
    if request.method == "POST":
        form = EntradaCompraForm(request.POST)
        formset = EntradaDetalleCompraFormSet(request.POST, prefix="detalles", form_kwargs={"proveedor": proveedor})
        if form.is_valid() and formset.is_valid():
            clave = form.cleaned_data["clave_idempotencia"]
            existente = Compra.objects.using(db_alias).filter(clave_idempotencia=clave).first()
            if existente:
                messages.info(request, "Esta entrada ya se había registrado; se abrió su detalle.")
                return redirect("compras:detalle_compra", id=existente.id_compra)

            try:
                with transaction.atomic(using=db_alias):
                    compra = form.save(commit=False)
                    compra.clave_idempotencia = clave
                    compra.estado = "recibida"
                    compra.usuario = request.user
                    compra.save(using=db_alias)

                    resumen = []
                    for detalle_form in formset.forms:
                        datos = detalle_form.cleaned_data
                        if not datos or datos.get("DELETE"):
                            continue
                        material = MaterialConstruccion.objects.using(db_alias).select_for_update().select_related(
                            "unidad_medida"
                        ).get(pk=datos["material"].pk, activo=True)
                        if not ProveedorMaterial.objects.using(db_alias).select_for_update().filter(proveedor=compra.proveedor, material=material, activo=True).exists():
                            raise ValidationError("El material no está asociado a este proveedor.")
                        precio_venta_actual = material.precio_referencia
                        if datos.get("actualizar_precio_venta"):
                            material.precio_referencia = datos["precio_venta_unitario"]
                            material.save(using=db_alias, update_fields=["precio_referencia"])
                            precio_venta_actual = material.precio_referencia

                        detalle = DetalleCompra(
                            compra=compra,
                            material=material,
                            cantidad=datos["cantidad"],
                            precio_unitario=datos["precio_unitario"],
                            material_nombre=material.nombre,
                            unidad_medida_nombre=material.unidad_medida.nombre,
                            unidad_medida_abreviatura=material.unidad_medida.abreviatura,
                            precio_venta_unitario=precio_venta_actual,
                        )
                        detalle.save(using=db_alias)
                        movimiento = KardexService.registrar_movimiento(
                            material_id=material.pk,
                            tipo="entrada",
                            cantidad=detalle.cantidad,
                            observacion=(
                                f"Entrada {compra.numero_orden}"
                                + (f" · Factura {compra.numero_factura}" if compra.numero_factura else "")
                            ),
                            usuario=request.user,
                            compra_id=compra.pk,
                            using=db_alias,
                        )
                        resumen.append(
                            f"{detalle.material_nombre}: +{detalle.cantidad} "
                            f"({movimiento.stock_anterior} → {movimiento.stock_posterior})"
                        )

                    compra.calcular_total(using=db_alias)
                    registrar_actividad(
                        request,
                        "crear",
                        "compras",
                        compra.id_compra,
                        f"Entrada {compra.numero_orden} registrada: {', '.join(resumen)}",
                    )
                messages.success(request, f"Entrada registrada. {'; '.join(resumen)}")
                return redirect("compras:detalle_compra", id=compra.id_compra)
            except (ValidationError, ValueError, MaterialConstruccion.DoesNotExist) as exc:
                mensaje = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
                messages.error(request, f"No se pudo registrar la entrada: {mensaje}")
            except IntegrityError:
                existente = Compra.objects.using(db_alias).filter(clave_idempotencia=clave).first()
                if existente:
                    messages.info(request, "La entrada ya fue procesada.")
                    return redirect("compras:detalle_compra", id=existente.id_compra)
                messages.error(request, "No se pudo guardar la entrada por una restricción de integridad.")
    else:
        initial = {"clave_idempotencia": uuid.uuid4()}
        proveedor_id = request.GET.get("proveedor")
        if proveedor_id:
            initial["proveedor"] = proveedor_id
        form = EntradaCompraForm(initial=initial)
        formset = EntradaDetalleCompraFormSet(prefix="detalles", form_kwargs={"proveedor": proveedor})

    materiales = MaterialConstruccion.objects.using(db_alias).filter(activo=True).select_related(
        "unidad_medida", "stock_info"
    ).order_by("nombre")
    return render(
        request,
        "compras/crear_entrada.html",
        {"form": form, "formset": formset, "proveedor": proveedor, "tiene_materiales": proveedor and proveedor.materiales_ofertados.filter(activo=True, material__activo=True).exists()},
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
        nuevo_estado = request.POST.get("estado")
        db_alias = router.db_for_write(Compra)
        try:
            with transaction.atomic(using=db_alias):
                compra = get_object_or_404(
                    select_for_update_if_supported(Compra.objects.using(db_alias), db_alias), id_compra=id
                )
                if nuevo_estado == "recibida":
                    raise ValidationError("Una compra solo se marca recibida al registrar su entrada de inventario.")
                motivo = (request.POST.get("motivo_anulacion") or "").strip()
                if nuevo_estado == "cancelada" and compra.estado == "recibida":
                    if not motivo:
                        raise ValidationError("Indica el motivo para anular y revertir esta entrada.")
                    for detalle in compra.detalles.using(db_alias).select_related("material"):
                        KardexService.registrar_movimiento(
                            material_id=detalle.material_id,
                            tipo="salida",
                            cantidad=detalle.cantidad,
                            observacion=f"Reversión de entrada {compra.numero_orden}: {motivo}",
                            usuario=request.user,
                            compra_id=compra.pk,
                            using=db_alias,
                        )
                compra.transicionar(nuevo_estado)
                compra.motivo_anulacion = motivo
                compra.save(using=db_alias, update_fields=["estado", "motivo_anulacion"])
                registrar_actividad(
                    request,
                    "editar",
                    "compras",
                    compra.id_compra,
                    f"Estado de compra {compra.numero_orden} cambiado a {nuevo_estado}",
                )
            messages.success(request, f"Estado actualizado a {compra.get_estado_display()}.")
        except (ValidationError, ValueError) as err:
            mensaje = "; ".join(err.messages) if hasattr(err, "messages") else str(err)
            messages.error(request, f"No fue posible cambiar el estado: {mensaje}")
        return redirect("compras:detalle_compra", id=compra.id_compra)
    return redirect("compras:lista_compras")


@admin_required
def editar_compra(request, id):
    compra = get_object_or_404(Compra, id_compra=id)
    messages.info(
        request,
        "El historial de compras es solo de consulta y no se puede editar.",
    )
    return redirect("compras:detalle_compra", id=compra.id_compra)


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
        {
            "type": "text",
            "name": "nombre",
            "placeholder": "Nombre / Empresa",
            "value": nombre,
            "size": "3",
        },
        {"type": "text", "name": "nit", "placeholder": "NIT", "value": nit, "size": "2"},
        {
            "type": "text",
            "name": "contacto",
            "placeholder": "Contacto / Teléfono",
            "value": contacto,
            "size": "3",
        },
        {"type": "text", "name": "ciudad", "placeholder": "Ciudad", "value": ciudad, "size": "2"},
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

    context = {
        "proveedores": proveedores,
        "query": query,
        "nombre": nombre,
        "nit": nit,
        "contacto": contacto,
        "ciudad": ciudad,
        "estado_actual": estado,
        "categoria": categoria,
        "filter_fields": filter_fields,
    }

    if (
        request.headers.get("x-requested-with") == "XMLHttpRequest"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    ):
        return render(request, "compras/_proveedores_body.html", context)

    return render(request, "compras/proveedores_lista.html", context)


@admin_required
def crear_proveedor(request):
    if request.method == "POST":
        data = request.POST.copy()
        if "email" in data:
            if not data.get("correo"):
                data["correo"] = data["email"]
            data.pop("email", None)
        form = ProveedorForm(data)
        if form.is_valid():
            proveedor = form.save()
            registrar_actividad(
                request,
                "crear",
                "proveedores",
                proveedor.nit,
                f"Proveedor creado: {proveedor.nombre_empresa}",
            )
            messages.success(request, "Proveedor registrado con éxito.")
            return redirect("compras:perfil_proveedor", codigo_proveedor=proveedor.codigo_proveedor)
        logger.warning("[PROVEEDOR_FORM_ERROR] Errores al registrar proveedor: %s | Data: %s", form.errors.as_json(), dict(data))
        messages.error(request, "Revisa los datos del proveedor e inténtalo nuevamente.")
        return render(
            request,
            "compras/proveedor_form.html",
            {"action": "Crear", "form": form, "form_data": request.POST},
        )
    else:
        form = ProveedorForm()
    return render(
        request,
        "compras/proveedor_form.html",
        {"action": "Crear", "form": form},
    )


@admin_required
def editar_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)
    if request.method == "POST":
        data = request.POST.copy()
        if "email" in data:
            if not data.get("correo"):
                data["correo"] = data["email"]
            data.pop("email", None)
        form = ProveedorForm(data, instance=proveedor)
        if form.is_valid():
            proveedor = form.save()
            registrar_actividad(
                request,
                "editar",
                "proveedores",
                proveedor.nit,
                f"Proveedor editado: {proveedor.nombre_empresa}",
            )
            messages.success(request, "Proveedor actualizado.")
            return redirect(
                "compras:perfil_proveedor",
                codigo_proveedor=proveedor.codigo_proveedor,
            )
        logger.warning("[PROVEEDOR_FORM_ERROR] Errores al editar proveedor: %s | Data: %s", form.errors.as_json(), dict(data))
        messages.error(request, "Revisa los datos del proveedor e inténtalo nuevamente.")
        return render(
            request,
            "compras/proveedor_form.html",
            {"proveedor": proveedor, "action": "Editar", "form": form, "form_data": request.POST},
        )
    else:
        form = ProveedorForm(instance=proveedor)
    return render(
        request,
        "compras/proveedor_form.html",
        {"form": form, "proveedor": proveedor, "action": "Editar"},
    )


@admin_required
def perfil_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)

    detalles_base = DetalleCompra.objects.filter(compra__proveedor=proveedor)
    detalles_compra = list(
        detalles_base
        .select_related("compra", "material", "material__unidad_medida")
        .order_by("-compra__fecha_compra", "-id_detalle_compra")
    )

    compras_validas = Compra.objects.filter(proveedor=proveedor, estado="recibida")
    total_comprado = sum((c.total_compra or Decimal("0") for c in compras_validas), Decimal("0"))
    total_entradas = compras_validas.count()
    ultima_compra = (
        compras_validas.order_by("-fecha_compra").values_list("fecha_compra", flat=True).first()
    )

    material_frecuente = "Sin compras"
    if detalles_compra:
        conteo_materiales = {}
        for det in detalles_compra:
            nombre_mat = det.material_nombre or det.material.nombre
            conteo_materiales[nombre_mat] = conteo_materiales.get(nombre_mat, 0) + int(
                det.cantidad or 0
            )
        if conteo_materiales:
            material_frecuente = max(conteo_materiales.items(), key=lambda x: x[1])[0]

    fecha_desde = request.GET.get("fecha_desde", "").strip()
    fecha_hasta = request.GET.get("fecha_hasta", "").strip()
    filtro_material = request.GET.get("material", "").strip()
    factura = request.GET.get("factura", "").strip()
    detalles_filtrados = detalles_base
    if fecha_desde:
        detalles_filtrados = detalles_filtrados.filter(compra__fecha_compra__date__gte=fecha_desde)
    if fecha_hasta:
        detalles_filtrados = detalles_filtrados.filter(compra__fecha_compra__date__lte=fecha_hasta)
    if filtro_material:
        detalles_filtrados = detalles_filtrados.filter(
            Q(material_nombre__icontains=filtro_material) | Q(material__nombre__icontains=filtro_material)
        )
    if factura:
        filtros_factura = Q(compra__numero_factura__icontains=factura)
        if factura.isdigit():
            filtros_factura |= Q(compra__id_compra=int(factura))
        detalles_filtrados = detalles_filtrados.filter(filtros_factura)

    return render(
        request,
        "compras/proveedor_perfil.html",
        {
            "proveedor": proveedor,
            "historial_compras": detalles_filtrados.select_related("compra", "material", "material__unidad_medida").order_by("-compra__fecha_compra"),
            "total_comprado": total_comprado,
            "total_entradas": total_entradas,
            "ultima_compra": ultima_compra,
            "material_frecuente": material_frecuente,
            "materiales_asociados": proveedor.materiales_ofertados.select_related("material", "material__unidad_medida"),
            "materiales_suministrados": sorted({d.material_nombre or d.material.nombre for d in detalles_compra}),
            "filtros_historial": {"fecha_desde": fecha_desde, "fecha_hasta": fecha_hasta, "material": filtro_material, "factura": factura},
        },
    )


@admin_required
def catalogo_proveedor(request, codigo_proveedor):
    proveedor = get_object_or_404(Proveedor, codigo_proveedor=codigo_proveedor)
    if request.method == "POST":
        formset = ProveedorMaterialFormSet(request.POST, instance=proveedor, prefix="catalogo")
        if formset.is_valid():
            db_alias = router.db_for_write(ProveedorMaterial)
            with transaction.atomic(using=db_alias):
                formset.save()
            registrar_actividad(
                request, "editar", "proveedores", proveedor.nit,
                f"Catálogo de materiales actualizado para {proveedor.nombre_empresa}",
            )
            messages.success(request, "Catálogo del proveedor actualizado. El inventario no fue modificado.")
            return redirect("compras:perfil_proveedor", codigo_proveedor=proveedor.codigo_proveedor)
        messages.error(request, "Revisa los materiales y precios de compra ofertados.")
    else:
        formset = ProveedorMaterialFormSet(instance=proveedor, prefix="catalogo")
    catalogo = proveedor.materiales_ofertados.select_related("material", "material__unidad_medida").order_by("material__nombre")
    return render(request, "compras/proveedor_catalogo.html", {"proveedor": proveedor, "formset": formset, "catalogo": catalogo})


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
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("compras:lista_proveedores")
    return redirect(next_url)


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
            "fecha_actualizacion": item.fecha_actualizacion.strftime("%d/%m/%Y %I:%M %p"),
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
