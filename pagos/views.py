import json
from datetime import datetime

from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render, get_object_or_404


from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ordenes.models import Pedido
from usuarios.models import MetodoPago
from usuarios.views import admin_required

from .models import Pago, PagoPedido
from ordenes.models import Pedido
from .prototype import (
    append_history_entry,
    assign_transport,
    calculate_order_totals,
    generate_order_code,

    assign_transport,
    calculate_order_totals,
    generate_order_code,
    mark_delivery,
    seed_demo_state,
    update_payment_and_order_status,
)
from .services import registrar_estado_pago



@admin_required
def lista_pagos(request):
    cliente = request.GET.get("cliente", "")
    factura = request.GET.get("factura", "")
    referencia = request.GET.get("referencia", "")
    fecha = request.GET.get("fecha", "")
    metodo = request.GET.get("metodo", "")
    q = request.GET.get("q", "")

    pagos = (
        Pago.objects.select_related(
            "factura", "factura__cliente", "registrado_por", "codigo_metodo_pago"
        )
        .all()
        .order_by("-fecha")
    )

    if cliente:
        pagos = pagos.filter(
            Q(factura__cliente__nombres__icontains=cliente)
            | Q(factura__cliente__apellidos__icontains=cliente)
        )
    if factura:
        pagos = pagos.filter(factura__numero__icontains=factura)
    if referencia:
        pagos = pagos.filter(referencia__icontains=referencia)

    if fecha:
        pagos = pagos.filter(fecha__date=fecha)

    if metodo:
        pagos = pagos.filter(codigo_metodo_pago__codigo_metodo_pago=metodo)
    
    if q:
        pagos = pagos.filter(
            Q(factura__cliente__nombres__icontains=q)
            | Q(factura__cliente__apellidos__icontains=q)
            | Q(factura__numero__icontains=q)
            | Q(referencia__icontains=q)
        )

    # Prepare filter fields for template
    filter_fields = [
        {"type": "text", "name": "cliente", "placeholder": "Cliente", "value": cliente, "size": "2"},
        {"type": "text", "name": "factura", "placeholder": "N° Factura", "value": factura, "size": "2"},
        {"type": "text", "name": "referencia", "placeholder": "Referencia", "value": referencia, "size": "2"},
        {"type": "date", "name": "fecha", "placeholder": "Fecha", "value": fecha, "size": "2"},
        {"type": "select", "name": "metodo", "placeholder": "Método (Todos)", "value": metodo, "size": "2",
         "options": [{"value": mp.codigo_metodo_pago, "label": mp.metodo} for mp in MetodoPago.objects.all()]},
    ]

    has_filters = any([cliente, factura, referencia, fecha, metodo, q])

    context = {
        "pagos": pagos,
        "cliente": cliente,
        "factura": factura,
        "referencia": referencia,
        "fecha": fecha,
        "metodo": metodo,
        "q": q,
        "filter_fields": filter_fields,
        "has_filters": has_filters,
        "metodos_pago": MetodoPago.objects.all(),
    }

    return render(request, "pagos/lista.html", context)


# =====================================================================
# GESTIÓN DE PAGOS (admin)
# =====================================================================
@admin_required
def gestion_pagos(request):
    """Vista de administración: revisar comprobantes y aprobar/rechazar pagos."""
    from django.db import OperationalError

    db_missing = False
    pedidos = []
    try:
        pedidos = (
            Pedido.objects.select_related("cliente__usuario")
            .prefetch_related("pagos_pedido")
            .order_by("-fecha_solicitud")
        )
        if request.method == "POST":
            pago_id = request.POST.get("pago_id")
            accion = request.POST.get("accion")
            pago = get_object_or_404(PagoPedido, pk=pago_id)
            pedido = pago.pedido
            if accion == "aprobar":
                registrar_estado_pago(pago, pedido, "pago aprobado")
                pago.save()
                pedido.save()
                messages.success(request, "Pago aprobado correctamente.")
            elif accion == "rechazar":
                motivo = request.POST.get("motivo_rechazo", "")
                registrar_estado_pago(pago, pedido, "pago rechazado", motivo_rechazo=motivo)
                pago.save()
                pedido.save()
                messages.warning(request, "Pago rechazado.")
            return redirect("pagos:gestion_pagos")
    except OperationalError:
        db_missing = True

    return render(request, "pagos/gestion_pagos.html", {
        "pedidos": pedidos,
        "db_missing_pagos_table": db_missing,
    })


# =====================================================================
# PROTOTIPO — helpers de sesión
# =====================================================================
def _get_proto_state(request):
    state = request.session.get("proto_state", {})
    return seed_demo_state(state)


def _save_proto_state(request, state):
    request.session["proto_state"] = state
    request.session.modified = True


def _get_order(state, order_id):
    return next((o for o in state.get("orders", []) if o["id"] == order_id), None)


# =====================================================================
# PROTOTIPO — vista general
# =====================================================================
def prototype_home(request):
    state = _get_proto_state(request)
    _save_proto_state(request, state)
    return render(request, "pagos/prototipo_home.html", {"state": state})


# =====================================================================
# PROTOTIPO — crear pedido
# =====================================================================
MATERIALS_CATALOG = [
    {"name": "Cemento", "unit_price": 45000},
    {"name": "Arena", "unit_price": 18000},
    {"name": "Grava", "unit_price": 22000},
    {"name": "Varilla", "unit_price": 120000},
    {"name": "Ladrillo", "unit_price": 800},
    {"name": "Bloque", "unit_price": 2500},
    {"name": "Puntilla", "unit_price": 5000},
    {"name": "Pintura", "unit_price": 75000},
    {"name": "Madera", "unit_price": 35000},
    {"name": "Tubería PVC", "unit_price": 28000},
]

PRICE_MAP = {m["name"]: m["unit_price"] for m in MATERIALS_CATALOG}


def prototype_order_form(request):
    state = _get_proto_state(request)

    if request.method == "POST":
        names = request.POST.getlist("material_name")
        quantities = request.POST.getlist("material_quantity")
        units = request.POST.getlist("material_unit")

        materials = []
        for name, qty, unit in zip(names, quantities, units):
            try:
                qty_int = int(qty)
            except (ValueError, TypeError):
                qty_int = 0
            unit_price = PRICE_MAP.get(name, 0)
            if qty_int > 0:
                materials.append({
                    "name": name,
                    "quantity": qty_int,
                    "unit": unit,
                    "unit_price": unit_price,
                })

        totals = calculate_order_totals(materials)
        new_order = {
            "id": generate_order_code(state.get("orders", [])),
            "customer": request.POST.get("customer", ""),
            "phone": request.POST.get("phone", ""),

            "delivery_address": request.POST.get("delivery_address", ""),
            "delivery_date": request.POST.get("delivery_date", ""),
            "observations": request.POST.get("observations", ""),
            "materials": materials,
            "subtotal": totals["subtotal"],
            "iva": totals["iva"],
            "total": totals["total"],
            "payment_method": None,

            "payment_status": "Pendiente",
            "order_status": "Pendiente de pago",
            "proof": None,
            "rejection_reason": None,
            "assigned_vehicle": None,
            "assigned_driver": None,
            "transport_date": None,
            "transport_time": None,
            "transport_notes": None,
            "history": [],
        }
        append_history_entry(new_order, "Pedido creado.")
        orders = state.setdefault("orders", [])
        orders.append(new_order)
        state["active_order_id"] = new_order["id"]
        _save_proto_state(request, state)
        return redirect("pagos:prototype_payment_method", order_id=new_order["id"])

    return render(request, "pagos/prototipo_pedido.html", {
        "state": state,
        "materials_catalog": MATERIALS_CATALOG,
    })


# =====================================================================
# PROTOTIPO — método de pago
# =====================================================================
PAYMENT_METHODS = [
    "Transferencia Bancolombia",
    "Nequi",
    "Daviplata",
    "Contra entrega",
]


def prototype_payment_method(request, order_id):
    state = _get_proto_state(request)
    order = _get_order(state, order_id)
    if order is None:
        return redirect("pagos:prototype_home")

    if request.method == "POST":
        method = request.POST.get("payment_method")
        if method:
            order["payment_method"] = method
            append_history_entry(order, "Método de pago seleccionado.")

            proof_file = request.FILES.get("proof")
            if proof_file:
                order["proof"] = {"name": proof_file.name, "size": f"{proof_file.size / 1024:.1f} KB", "type": proof_file.content_type}
                update_payment_and_order_status(order, "Comprobante enviado")
                append_history_entry(order, "Comprobante cargado.")
            elif method == "Contra entrega":
                update_payment_and_order_status(order, "Contra entrega")

            _save_proto_state(request, state)
            return redirect("pagos:prototype_payment_method", order_id=order_id)

    return render(request, "pagos/prototipo_metodo_pago.html", {
        "state": state,
        "order": order,
        "payment_methods": PAYMENT_METHODS,
    })


# =====================================================================
# PROTOTIPO — mis pedidos (cliente)
# =====================================================================
def prototype_customer_orders(request):
    state = _get_proto_state(request)
    orders = state.get("orders", [])
    selected_order_id = request.GET.get("order_id")
    selected_order = _get_order(state, selected_order_id) if selected_order_id else None

    if request.method == "POST":
        action = request.POST.get("action")
        o_id = request.POST.get("order_id", state.get("active_order_id"))
        order = _get_order(state, o_id)
        if order and action == "upload_new_proof":
            proof_file = request.FILES.get("proof")
            if proof_file:
                order["proof"] = {"name": proof_file.name, "size": f"{proof_file.size / 1024:.1f} KB", "type": proof_file.content_type}
                update_payment_and_order_status(order, "Comprobante enviado")
        _save_proto_state(request, state)
        return redirect("pagos:prototype_customer_orders")

    return render(request, "pagos/prototipo_mis_pedidos.html", {
        "state": state,
        "orders": orders,
        "selected_order": selected_order,
    })


# =====================================================================
# PROTOTIPO — detalle de pedido
# =====================================================================
def prototype_order_detail(request, order_id):
    state = _get_proto_state(request)
    order = _get_order(state, order_id)
    if order is None:
        return redirect("pagos:prototype_home")

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "approve_payment":
            update_payment_and_order_status(order, "Pago aprobado")

        elif action == "reject_payment":
            reason = request.POST.get("rejection_reason", "Sin motivo")
            order["rejection_reason"] = reason
            update_payment_and_order_status(order, "Pago rechazado")

        elif action == "authorize_dispatch":
            update_payment_and_order_status(order, "Pago aprobado")

        elif action == "assign_transport":
            assign_transport(
                order,
                vehicle=request.POST.get("vehicle", ""),
                driver=request.POST.get("driver", ""),
                transport_date=request.POST.get("transport_date", ""),
                transport_time=request.POST.get("transport_time", ""),
                notes=request.POST.get("transport_notes", ""),
            )

        elif action == "upload_new_proof":
            proof_file = request.FILES.get("proof")
            if proof_file:
                order["proof"] = {"name": proof_file.name, "size": f"{proof_file.size / 1024:.1f} KB", "type": proof_file.content_type}
                update_payment_and_order_status(order, "Comprobante enviado")

        _save_proto_state(request, state)
        return redirect("pagos:prototype_order_detail", order_id=order_id)

    return render(request, "pagos/prototipo_detalle.html", {
        "state": state,
        "order": order,
    })


# =====================================================================
# PROTOTIPO — panel admin
# =====================================================================
def prototype_admin_orders(request):
    state = _get_proto_state(request)
    return render(request, "pagos/prototipo_admin.html", {
        "state": state,
        "orders": state.get("orders", []),
    })


# =====================================================================
# PROTOTIPO — panel conductor
# =====================================================================
def prototype_conductor(request):
    state = _get_proto_state(request)

    orders = state.get("orders", [])

    if request.method == "POST":
        action = request.POST.get("action")
        o_id = request.POST.get("order_id")
        order = _get_order(state, o_id)
        if order and action == "mark_delivery":
            collected = request.POST.get("delivery_result") == "yes"
            mark_delivery(order, collected)
            _save_proto_state(request, state)
        return redirect("pagos:prototype_conductor")

    assigned = [o for o in orders if o.get("assigned_driver")]
    return render(request, "pagos/prototipo_conductor.html", {
        "state": state,
        "orders": assigned,
    })


# =====================================================================
# PROTOTIPO — cambio de rol
# =====================================================================
def prototype_switch_role(request, role):
    state = _get_proto_state(request)
    state["role"] = role
    _save_proto_state(request, state)
    return redirect("pagos:prototype_home")

