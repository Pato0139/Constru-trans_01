from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.facturacion.models import Factura
from apps.usuarios.models import MetodoPago
from apps.usuarios.views import admin_required

from .models import Pago
from .services import crear_notificacion_pago


@admin_required
def lista_pagos(request):
    q = request.GET.get("q", "")
    fecha = request.GET.get("fecha", "")
    metodo = request.GET.get("metodo", "")
    estado = request.GET.get("estado", "")

    pagos = (
        Pago.objects.select_related(
            "factura", "factura__cliente", "registrado_por", "codigo_metodo_pago"
        )
        .all()
        .order_by("-fecha")
    )

    if q:
        pagos = pagos.filter(
            Q(factura__numero__icontains=q)
            | Q(factura__cliente__nombres__icontains=q)
            | Q(factura__cliente__apellidos__icontains=q)
            | Q(referencia__icontains=q)
        )

    if fecha:
        pagos = pagos.filter(fecha__date=fecha)

    if metodo:
        pagos = pagos.filter(codigo_metodo_pago__codigo_metodo_pago=metodo)

    if estado:
        pagos = pagos.filter(estado=estado)

    context = {
        "pagos": pagos,
        "q": q,
        "fecha": fecha,
        "metodo": metodo,
        "estado": estado,
        "metodos_pago": MetodoPago.objects.all(),
        "estados_pago": Pago.ESTADOS_PAGO,
    }

    return render(request, "pagos/lista.html", context)


@login_required
def detalle_pago(request, id_pago):
    pago = get_object_or_404(Pago, id_pago=id_pago)
    # Verificar que el usuario sea el cliente del pedido o admin
    if (
        not request.user.is_superuser
        and not (hasattr(request.user, "rol") and request.user.rol == "admin")
        and pago.factura.cliente != request.user
    ):
        messages.error(request, "No tienes permisos para ver este pago.")
        return redirect("inicio:inicio")

    context = {"pago": pago}
    return render(request, "pagos/detalle.html", context)


@login_required
def procesar_pago(request, id_factura):
    factura = get_object_or_404(Factura, id_factura=id_factura)

    # Verificar que el usuario sea el cliente del pedido o admin
    if (
        not request.user.is_superuser
        and not (hasattr(request.user, "rol") and request.user.rol == "admin")
        and factura.cliente != request.user
    ):
        messages.error(request, "No tienes permisos para pagar esta factura.")
        return redirect("inicio:inicio")

    if factura.estado == "pagada":
        messages.info(request, "Esta factura ya está pagada.")
        return redirect("facturacion:detalle_factura", id_factura=factura.id_factura)

    if request.method == "POST":
        metodo_pago_codigo = request.POST.get("metodo_pago")
        monto = request.POST.get("monto", factura.saldo_pendiente)
        referencia = request.POST.get("referencia", "")
        notas = request.POST.get("notas", "")

        try:
            monto = float(monto)
            if monto <= 0:
                raise ValueError("El monto debe ser positivo")
        except (ValueError, TypeError):
            messages.error(request, "Monto inválido.")
            return render(
                request,
                "pagos/procesar_pago.html",
                {"factura": factura, "metodos_pago": MetodoPago.objects.all()},
            )

        metodo_pago = get_object_or_404(MetodoPago, codigo_metodo_pago=metodo_pago_codigo)

        # Crear el pago
        pago = Pago.objects.create(
            factura=factura,
            monto=monto,
            codigo_metodo_pago=metodo_pago,
            referencia=referencia,
            notas=notas,
            registrado_por=request.user,
            estado="pendiente",  # Por defecto pendiente, admin lo puede marcar como completado
        )

        # Manejar comprobante si se subió
        if "comprobante" in request.FILES:
            pago.comprobante = request.FILES["comprobante"]
            pago.save()

        # Si es efectivo y el usuario es admin, marcar como completado directamente
        if metodo_pago_codigo == "EFE" and (
            request.user.is_superuser
            or (hasattr(request.user, "rol") and request.user.rol == "admin")
        ):
            pago.estado = "completado"
            pago.save()

        # Crear notificación
        crear_notificacion_pago(request.user, pago)

        messages.success(request, "¡Pago registrado exitosamente!")
        return redirect("pagos:detalle_pago", id_pago=pago.id_pago)

    context = {
        "factura": factura,
        "metodos_pago": MetodoPago.objects.all(),
        "saldo_pendiente": factura.saldo_pendiente,
    }
    return render(request, "pagos/procesar_pago.html", context)


@admin_required
def actualizar_estado_pago(request, id_pago):
    pago = get_object_or_404(Pago, id_pago=id_pago)
    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")
        if nuevo_estado in dict(Pago.ESTADOS_PAGO):
            pago.estado = nuevo_estado
            pago.save()
            # Notificar al cliente
            if pago.factura.cliente:
                crear_notificacion_pago(pago.factura.cliente, pago)
            messages.success(request, "Estado del pago actualizado correctamente!")
    return redirect("pagos:detalle_pago", id_pago=pago.id_pago)
