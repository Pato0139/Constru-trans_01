from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.security import (
    _respuesta_no_autorizada,
    obtener_ip,
    registrar_evento,
    registrar_warning,
    role_required,
)
from pagos.models import Pago
from usuarios.models import MetodoPago
from usuarios.views import admin_required
from clientes.models import Cliente

from .models import Factura


@admin_required
def lista_facturas(request):
    estado = request.GET.get("estado", "")
    cliente = request.GET.get("cliente", "")
    factura = request.GET.get("factura", "")
    q = request.GET.get("q", "")

    qs = Factura.objects.select_related("cliente", "cliente__usuario", "pedido").prefetch_related("pagos")

    if estado in ["pendiente", "pagada", "anulada"]:
        qs = qs.filter(estado=estado)
    if cliente:
        qs = qs.filter(
            Q(cliente__usuario__nombres__icontains=cliente)
            | Q(cliente__usuario__apellidos__icontains=cliente)
            | Q(cliente__usuario__documento__icontains=cliente)
        )
    if factura:
        qs = qs.filter(numero__icontains=factura)
    if q:
        qs = qs.filter(
            Q(numero__icontains=q)
            | Q(cliente__usuario__nombres__icontains=q)
            | Q(cliente__usuario__apellidos__icontains=q)
            | Q(cliente__usuario__documento__icontains=q)
        )

    filter_fields = [
        {"type": "text", "name": "cliente", "placeholder": "Cliente", "value": cliente, "size": "3"},
        {"type": "text", "name": "factura", "placeholder": "N° Factura", "value": factura, "size": "3"},
        {
            "type": "select",
            "name": "estado",
            "placeholder": "Estado (Todos)",
            "value": estado,
            "size": "3",
            "options": [
                {"value": "pendiente", "label": "Pendiente", "selected": estado == "pendiente"},
                {"value": "pagada", "label": "Pagada", "selected": estado == "pagada"},
                {"value": "anulada", "label": "Anulada", "selected": estado == "anulada"},
            ],
        },
    ]

    context = {
        "facturas": qs,
        "estado": estado,
        "cliente": cliente,
        "factura": factura,
        "q": q,
        "filter_fields": filter_fields,
        "has_filters": any([estado, cliente, factura, q]),
        "metodos_pago": MetodoPago.objects.all(),
    }

    return render(request, "facturacion/lista.html", context)


@login_required
def mis_facturas(request):
    user = request.user
    is_super = getattr(user, "is_superuser", False) or getattr(user, "es_superadmin", False)
    if is_super or user.rol == "admin":
        return redirect("facturacion:lista_facturas")

    if user.rol != "cliente":
        ip = obtener_ip(request)
        registrar_warning(ip)
        registrar_evento(
            request,
            "role_violation",
            gravedad="high",
            detalles={"causa": "mis_facturas_rol_invalido", "rol_usuario": user.rol},
        )
        return _respuesta_no_autorizada(
            request,
            detalles={"rol_requerido": ["cliente"], "rol_usuario": user.rol},
        )

    cliente = get_object_or_404(Cliente, usuario=user)
    facturas = (
        Factura.objects.filter(cliente=cliente).select_related("pedido").prefetch_related("pagos")
    )

    context = {"facturas": facturas, "metodos_pago": MetodoPago.objects.all()}

    return render(request, "facturacion/mis_facturas.html", context)


@login_required
@require_POST
def registrar_pago(request):
    factura_id = request.POST.get("factura_id")
    monto_str = request.POST.get("monto", "0")
    metodo_codigo = request.POST.get("metodo")

    try:
        monto = Decimal(monto_str)
    except Exception:
        return JsonResponse({"error": "Monto inválido"}, status=400)

    if monto <= 0:
        return JsonResponse({"error": "El monto debe ser mayor a cero"}, status=400)

    try:
        metodo_pago = MetodoPago.objects.get(codigo_metodo_pago=metodo_codigo)
    except MetodoPago.DoesNotExist:
        return JsonResponse({"error": "Método de pago inválido"}, status=400)

    try:
        with transaction.atomic():
            factura = Factura.objects.select_for_update().get(pk=factura_id)

            user = request.user
            is_super = getattr(user, "is_superuser", False) or getattr(user, "es_superadmin", False)
            es_admin = is_super or user.rol == "admin"
            es_propietario = factura.cliente_id and factura.cliente.usuario_id == user.pk

            if not (es_admin or es_propietario):
                ip = obtener_ip(request)
                registrar_warning(ip)
                registrar_evento(
                    request,
                    "role_violation",
                    gravedad="high",
                    detalles={
                        "causa": "registrar_pago_factura_ajena",
                        "factura_id": factura.pk,
                        "factura_numero": factura.numero,
                        "cliente_factura_id": factura.cliente_id,
                    },
                )
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "error": "No autorizado — intento registrado en sistema de seguridad.",
                            "security_warning": True,
                        },
                        status=403,
                    )
                return _respuesta_no_autorizada(
                    request,
                    detalles={
                        "rol_requerido": ["admin"],
                        "permiso_alternativo": "propietario de la factura",
                        "factura": factura.numero,
                    },
                )

            if factura.estado == "anulada":
                return JsonResponse({"error": "La factura está anulada"}, status=400)
            if factura.estado == "pagada":
                return JsonResponse(
                    {"error": "La factura ya ha sido pagada totalmente"}, status=400
                )

            if monto > factura.saldo_pendiente:
                return JsonResponse(
                    {"error": f"El monto excede el saldo pendiente (${factura.saldo_pendiente})"},
                    status=400,
                )

            Pago.objects.create(
                factura=factura,
                monto=monto,
                codigo_metodo_pago=metodo_pago,
                referencia=request.POST.get(
                    "referencia",
                    "Pago realizado por cliente" if not es_admin else "",
                ),
                registrado_por=request.user,
            )

            if factura.saldo_pendiente <= 0:
                factura.estado = "pagada"
                factura.save()
                mensaje_adicional = "Factura pagada por completo."
            else:
                mensaje_adicional = (
                    f"Pago parcial registrado. Monto por pagar: ${factura.saldo_pendiente}"
                )

        return JsonResponse(
            {
                "status": "ok",
                "estado": factura.get_estado_display(),
                "mensaje": mensaje_adicional,
                "saldo": float(factura.saldo_pendiente),
            }
        )
    except Factura.DoesNotExist:
        return JsonResponse({"error": "Factura no encontrada"}, status=404)


@admin_required
def anular_factura(request, id):
    factura = get_object_or_404(Factura, pk=id)
    if factura.estado == "pagada":
        return JsonResponse({"error": "No se puede anular una factura ya pagada"}, status=400)

    factura.estado = "anulada"
    factura.save()
    return JsonResponse({"status": "ok", "mensaje": "Factura anulada correctamente"})


@admin_required
def editar_factura_monto(request, id):
    factura = get_object_or_404(Factura, pk=id)
    if factura.estado != "pendiente":
        return JsonResponse(
            {"error": "Solo se pueden editar facturas en estado pendiente"}, status=400
        )

    try:
        nuevo_monto = Decimal(request.POST.get("monto"))
        if nuevo_monto <= 0:
            raise ValueError

        factura.subtotal = nuevo_monto / Decimal("1.19")
        factura.iva = nuevo_monto - factura.subtotal
        factura.total = nuevo_monto
        factura.save()

        if factura.orden:
            factura.orden.precio = nuevo_monto
            factura.orden.save()

        return JsonResponse({"status": "ok", "mensaje": "Monto de factura actualizado"})
    except Exception:
        return JsonResponse({"error": "Monto inválido"}, status=400)
