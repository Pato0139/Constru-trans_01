import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ordenes.models import Pedido
from usuarios.models import MetodoPago
from usuarios.views import admin_required

from .models import Pago, PagoPedido
from .services import registrar_estado_pago
from .prototype import (
    append_history_entry,
    assign_transport,
    calculate_order_totals,
    generate_order_code,
    mark_delivery,
    seed_demo_state,
    update_payment_and_order_status,
)


@admin_required
def lista_pagos(request):
    cliente = request.GET.get("cliente", "")
    factura = request.GET.get("factura", "")
    referencia = request.GET.get("referencia", "")
    fecha = request.GET.get("fecha", "")
    metodo = request.GET.get("metodo", "")

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

    context = {
        "pagos": pagos,
        "cliente": cliente,
        "factura": factura,
        "referencia": referencia,
        "fecha": fecha,
        "metodo": metodo,
        "metodos_pago": MetodoPago.objects.all(),
    }

    return render(request, "pagos/lista.html", context)


from django.db import DatabaseError

@login_required
@admin_required
def gestion_pagos(request):
    db_missing = False
    try:
        pedidos = (
            Pedido.objects.select_related("cliente__usuario", "conductor")
            .prefetch_related("pagos_pedido")
            .order_by("-fecha_solicitud")
        )
        pagos_qs = PagoPedido.objects.select_related("pedido", "cliente__usuario").all()
    except DatabaseError:
        # Evitamos que una tabla faltante rompa la vista; se muestra mensaje en la plantilla.
        pedidos = Pedido.objects.none()
        pagos_qs = PagoPedido.objects.none() if hasattr(PagoPedido, "objects") else []
        db_missing = True

    if request.method == "POST" and not db_missing:
        pago_id = request.POST.get("pago_id")
        accion = request.POST.get("accion")
        pago = get_object_or_404(PagoPedido, pk=pago_id)

        if accion == "aprobar":
            registrar_estado_pago(pago, pago.pedido, "pago aprobado")
            pago.agregar_historial(f"Pago aprobado por {request.user.username}")
            pago.save(update_fields=["estado_pago", "motivo_rechazo", "fecha_actualizacion"])
            messages.success(request, f"Pago aprobado para el pedido #{pago.pedido.codigo_pedido}.")
        elif accion == "rechazar":
            motivo = request.POST.get("motivo_rechazo", "").strip()
            if not motivo:
                messages.error(request, "Escribe un motivo para rechazar el comprobante.")
            else:
                pago.estado_pago = "pago rechazado"
                pago.motivo_rechazo = motivo
                pago.pedido.estado = "pendiente"
                pago.pedido.save(update_fields=["estado"])
                pago.agregar_historial(f"Pago rechazado por {request.user.username}: {motivo}")
                pago.save(update_fields=["estado_pago", "motivo_rechazo", "fecha_actualizacion"])
                messages.warning(request, "Pago rechazado y cliente notificado.")
        return redirect("pagos:gestion_pagos")

    context = {
        "pedidos": pedidos,
        "pagos_pedido": pagos_qs,
        "db_missing_pagos_table": db_missing,
    }
    return render(request, "pagos/gestion_pagos.html", context)


def _load_prototype_state(request):
    state = request.session.get("prototype_state", {})
    state.setdefault("orders", [])
    state.setdefault("role", "cliente")
    state.setdefault("active_order_id", None)
    return state


def _save_prototype_state(request, state):
    request.session["prototype_state"] = state
    request.session.modified = True


def _get_order(state, order_id):
    for order in state.get("orders", []):
        if order.get("id") == order_id:
            return order
    return None


def prototype_home(request):
    state = seed_demo_state(_load_prototype_state(request))
    _save_prototype_state(request, state)
    return render(request, "pagos/prototipo_home.html", {"state": state})


def prototype_order_form(request):
    state = seed_demo_state(_load_prototype_state(request))

    if request.method == "POST":
        materials_payload = request.POST.get("materials_json", "[]")
        try:
            materials = json.loads(materials_payload)
        except json.JSONDecodeError:
            materials = []

        materials = [
            {
                "name": item.get("name", "").strip(),
                "quantity": int(item.get("quantity", 0) or 0),
                "unit": item.get("unit", "u"),
                "unit_price": int(item.get("unit_price", 0) or 0),
            }
            for item in materials
            if item.get("name", "").strip() and int(item.get("quantity", 0) or 0) > 0
        ]

        if not materials:
            messages.error(request, "Agrega al menos un material para crear el pedido.")
            return redirect("pagos:prototype_order_form")

        totals = calculate_order_totals(materials)
        order_id = generate_order_code(state["orders"])
        order = {
            "id": order_id,
            "customer": request.POST.get("customer", "Cliente demo"),
            "phone": request.POST.get("phone", "3001234567"),
            "materials": materials,
            "delivery_address": request.POST.get("delivery_address", "Dirección por confirmar"),
            "delivery_date": request.POST.get("delivery_date", ""),
            "observations": request.POST.get("observations", ""),
            "subtotal": totals["subtotal"],
            "iva": totals["iva"],
            "total": totals["total"],
            "payment_method": "",
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
        append_history_entry(order, "Pedido creado.")
        state["orders"].insert(0, order)
        state["active_order_id"] = order["id"]
        state["role"] = "cliente"
        _save_prototype_state(request, state)
        messages.success(request, f"Pedido {order_id} creado correctamente.")
        return redirect("pagos:prototype_payment_method", order_id=order_id)

    context = {
        "state": state,
        "materials_catalog": [
            {"name": "Cemento", "unit": "sacos", "unit_price": 45000},
            {"name": "Arena", "unit": "m3", "unit_price": 22000},
            {"name": "Varilla", "unit": "rollos", "unit_price": 120000},
            {"name": "Bloques", "unit": "unidades", "unit_price": 1800},
        ],
    }
    return render(request, "pagos/prototipo_pedido.html", context)


def prototype_payment_method(request, order_id):
    state = seed_demo_state(_load_prototype_state(request))
    order = _get_order(state, order_id)
    if not order:
        return redirect("pagos:prototype_home")

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "")
        order["payment_method"] = payment_method
        append_history_entry(order, "Método de pago seleccionado.")

        if payment_method == "Contra entrega":
            order["payment_status"] = "Contra entrega"
            order["order_status"] = "Pendiente de pago"
            order["proof"] = None
            append_history_entry(order, "Pago contra entrega confirmado.")
            messages.success(request, "Método de pago registrado. El cobro se hará en la entrega.")
        else:
            proof = request.FILES.get("proof")
            if proof:
                order["proof"] = {
                    "name": proof.name,
                    "size": f"{round(proof.size / 1024 / 1024, 1):.1f} MB",
                    "type": proof.content_type,
                }
                order["payment_status"] = "Comprobante enviado"
                order["order_status"] = "Pendiente de revisión"
                append_history_entry(order, "Comprobante cargado.")
                messages.success(request, "Comprobante enviado. El administrador lo revisará pronto.")
            else:
                order["payment_status"] = "Pendiente"
                order["order_status"] = "Pendiente de pago"
                messages.info(request, "Selecciona el método y, si aplica, sube un comprobante.")

        _save_prototype_state(request, state)
        return redirect("pagos:prototype_customer_orders")

    context = {
        "state": state,
        "order": order,
        "payment_methods": [
            "Nequi",
            "Daviplata",
            "Transferencia Bancolombia",
            "Contra entrega",
        ],
    }
    return render(request, "pagos/prototipo_metodo_pago.html", context)


def prototype_customer_orders(request):
    state = seed_demo_state(_load_prototype_state(request))
    selected_order_id = request.GET.get("order_id") or state.get("active_order_id")
    selected_order = _get_order(state, selected_order_id) if selected_order_id else None

    context = {
        "state": state,
        "orders": state.get("orders", []),
        "selected_order": selected_order,
    }
    return render(request, "pagos/prototipo_mis_pedidos.html", context)


def prototype_order_detail(request, order_id):
    state = seed_demo_state(_load_prototype_state(request))
    order = _get_order(state, order_id)
    if not order:
        return redirect("pagos:prototype_home")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "upload_new_proof":
            proof = request.FILES.get("proof")
            if proof:
                order["proof"] = {
                    "name": proof.name,
                    "size": f"{round(proof.size / 1024 / 1024, 1):.1f} MB",
                    "type": proof.content_type,
                }
                order["payment_status"] = "Comprobante enviado"
                order["order_status"] = "Pendiente de revisión"
                append_history_entry(order, "Comprobante cargado.")
                messages.success(request, "Comprobante actualizado correctamente.")
            else:
                messages.error(request, "Adjunta un archivo válido para subir el comprobante.")
        elif action == "approve_payment":
            update_payment_and_order_status(order, "Pago aprobado")
            messages.success(request, "Pago aprobado. El pedido ya puede despacharse.")
        elif action == "reject_payment":
            reason = request.POST.get("rejection_reason", "").strip()
            if not reason:
                messages.error(request, "Escribe un motivo para rechazar el pago.")
            else:
                order["rejection_reason"] = reason
                update_payment_and_order_status(order, "Pago rechazado")
                messages.warning(request, "Pago rechazado. El cliente verá el motivo.")
        elif action == "authorize_dispatch":
            order["payment_status"] = "Contra entrega"
            order["order_status"] = "Autorizado para despacho"
            append_history_entry(order, "Pedido despachado.")
            messages.success(request, "Despacho autorizado para entrega.")
        elif action == "assign_transport":
            assign_transport(
                order,
                request.POST.get("vehicle", ""),
                request.POST.get("driver", ""),
                request.POST.get("transport_date", ""),
                request.POST.get("transport_time", ""),
                request.POST.get("transport_notes", ""),
            )
            messages.success(request, "Transporte asignado correctamente.")
        elif action == "mark_delivery":
            payment_collected = request.POST.get("delivery_result") == "yes"
            mark_delivery(order, payment_collected)
            if payment_collected:
                messages.success(request, "Entrega finalizada. Pago recibido.")
            else:
                messages.warning(request, "Entrega finalizada. Se registró incidencia de pago.")

        _save_prototype_state(request, state)
        return redirect("pagos:prototype_order_detail", order_id=order_id)

    context = {"state": state, "order": order}
    return render(request, "pagos/prototipo_detalle.html", context)


def prototype_admin_orders(request):
    state = seed_demo_state(_load_prototype_state(request))
    context = {"state": state, "orders": state.get("orders", [])}
    return render(request, "pagos/prototipo_admin.html", context)


def prototype_conductor(request):
    state = seed_demo_state(_load_prototype_state(request))
    assigned_orders = [
        order for order in state.get("orders", []) if order.get("assigned_driver") == "Carlos Morales"
    ]

    if request.method == "POST":
        action = request.POST.get("action")
        order_id = request.POST.get("order_id")
        order = _get_order(state, order_id)
        if action == "mark_delivery" and order:
            payment_collected = request.POST.get("delivery_result") == "yes"
            mark_delivery(order, payment_collected)
            _save_prototype_state(request, state)
            messages.success(request, "Se actualizó el estado del pedido.")
        return redirect("pagos:prototype_conductor")

    context = {"state": state, "orders": assigned_orders}
    return render(request, "pagos/prototipo_conductor.html", context)


def prototype_switch_role(request, role):
    state = _load_prototype_state(request)
    state["role"] = role
    _save_prototype_state(request, state)
    return redirect("pagos:prototype_home")
