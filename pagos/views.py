import json
from datetime import datetime

from django.contrib import messages
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, render

from usuarios.models import MetodoPago
from usuarios.views import admin_required

from .models import Pago, PagoPedido
from ordenes.models import Pedido
from .prototype import (
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


def get_prototype_state(request):
    state = request.session.get("pagos_prototype_state", {})
    if not state:
        state = seed_demo_state({})
        request.session["pagos_prototype_state"] = state
        request.session.modified = True
    return state


def save_prototype_state(request, state):
    request.session["pagos_prototype_state"] = state
    request.session.modified = True


def find_order(state, order_id):
    for order in state.get("orders", []):
        if str(order.get("id")) == str(order_id):
            return order
    return None


def prototype_home(request):
    state = get_prototype_state(request)
    return render(request, "pagos/prototipo_home.html", {"state": state})


def prototype_switch_role(request, role):
    state = get_prototype_state(request)
    if role not in ["cliente", "administrador", "conductor"]:
        messages.warning(request, "Rol no válido. Se mantiene el rol actual.")
        return redirect("pagos:prototype_home")
    state["role"] = role
    save_prototype_state(request, state)
    return redirect("pagos:prototype_home")


def prototype_order_form(request):
    state = get_prototype_state(request)
    materials_catalog = [
        {"name": "Cemento"},
        {"name": "Arena"},
        {"name": "Varilla"},
        {"name": "Bloques"},
    ]

    if request.method == "POST":
        materials_json = request.POST.get("materials_json", "[]")
        try:
            materials = json.loads(materials_json) if materials_json else []
        except ValueError:
            materials = []

        if not materials:
            material_names = request.POST.getlist("material_name")
            material_quantities = request.POST.getlist("material_quantity")
            material_units = request.POST.getlist("material_unit")
            for name, qty, unit in zip(material_names, material_quantities, material_units):
                materials.append(
                    {
                        "name": name,
                        "quantity": int(qty or 0),
                        "unit": unit,
                        "unit_price": 50000,
                    }
                )

        if not materials:
            messages.error(request, "Debe agregar al menos un material al pedido.")
            return render(request, "pagos/prototipo_pedido.html", {"materials_catalog": materials_catalog, "state": state})

        order = {
            "id": generate_order_code(state.get("orders", [])),
            "customer": request.POST.get("customer", "Cliente Demo"),
            "phone": request.POST.get("phone", "3000000000"),
            "delivery_address": request.POST.get("delivery_address", ""),
            "delivery_date": request.POST.get("delivery_date", ""),
            "observations": request.POST.get("observations", ""),
            "materials": materials,
            "subtotal": 0,
            "iva": 0,
            "total": 0,
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
            "history": [
                {"timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"), "text": "Pedido creado."}
            ],
        }
        totals = calculate_order_totals(order["materials"])
        order.update(totals)
        order["total"] = totals["total"]

        state["orders"] = state.get("orders", []) + [order]
        state["active_order_id"] = order["id"]
        save_prototype_state(request, state)

        messages.success(request, "Pedido creado correctamente.")
        return redirect("pagos:prototype_payment_method", order_id=order["id"])

    return render(request, "pagos/prototipo_pedido.html", {"materials_catalog": materials_catalog, "state": state})


def prototype_payment_method(request, order_id):
    state = get_prototype_state(request)
    order = find_order(state, order_id)
    if not order:
        messages.error(request, "Pedido no encontrado.")
        return redirect("pagos:prototype_home")

    payment_methods = ["Nequi", "Daviplata", "Transferencia Bancolombia", "Contra entrega"]

    if request.method == "POST":
        payment_method = request.POST.get("payment_method", "")
        if payment_method:
            order["payment_method"] = payment_method
            if payment_method == "Contra entrega":
                order["payment_status"] = "Contra entrega"
                order["order_status"] = "Pendiente de pago"
                order["proof"] = None
                order["history"].append({"timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"), "text": "Pago contra entrega seleccionado."})
            else:
                if request.FILES.get("proof"):
                    file = request.FILES["proof"]
                    order["proof"] = {
                        "name": file.name,
                        "size": f"{file.size / (1024 * 1024):.2f} MB",
                        "content_type": file.content_type,
                    }
                    order["payment_status"] = "Comprobante enviado"
                    order["order_status"] = "Pendiente de revisión"
                    order["history"].append({"timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"), "text": "Comprobante enviado."})
                else:
                    order["payment_status"] = "Pendiente"
                    order["history"].append({"timestamp": datetime.now().strftime("%d/%m/%Y %H:%M"), "text": "Método de pago seleccionado."})
            save_prototype_state(request, state)
            messages.success(request, "Método de pago actualizado.")
            return redirect("pagos:prototype_payment_method", order_id=order_id)

    return render(request, "pagos/prototipo_metodo_pago.html", {"order": order, "payment_methods": payment_methods, "state": state})


def prototype_customer_orders(request):
    state = get_prototype_state(request)
    return render(request, "pagos/prototipo_mis_pedidos.html", {"state": state, "orders": state.get("orders", [])})


def prototype_order_detail(request, order_id):
    state = get_prototype_state(request)
    order = find_order(state, order_id)
    if not order:
        messages.error(request, "Pedido no encontrado.")
        return redirect("pagos:prototype_home")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve_payment":
            update_payment_and_order_status(order, "Pago aprobado")
            messages.success(request, "Pago aprobado.")
        elif action == "reject_payment":
            order["payment_status"] = "Pago rechazado"
            order["rejection_reason"] = request.POST.get("rejection_reason", "")
            update_payment_and_order_status(order, "Pago rechazado")
            messages.warning(request, "Pago rechazado.")
        elif action == "authorize_dispatch":
            order["order_status"] = "Autorizado para despacho"
            messages.success(request, "Despacho autorizado.")
        elif action == "assign_transport":
            vehicle = request.POST.get("vehicle", "")
            driver = request.POST.get("driver", "")
            transport_date = request.POST.get("transport_date", "")
            transport_time = request.POST.get("transport_time", "")
            notes = request.POST.get("transport_notes", "")
            assign_transport(order, vehicle, driver, transport_date, transport_time, notes)
            messages.success(request, "Transporte asignado.")
        save_prototype_state(request, state)
        return redirect("pagos:prototype_order_detail", order_id=order_id)

    return render(request, "pagos/prototipo_detalle.html", {"order": order, "state": state})


def prototype_admin_orders(request):
    state = get_prototype_state(request)
    return render(request, "pagos/prototipo_admin.html", {"orders": state.get("orders", []), "state": state})


def prototype_conductor(request):
    state = get_prototype_state(request)
    orders = state.get("orders", [])

    if request.method == "POST":
        action = request.POST.get("action")
        order_id = request.POST.get("order_id")
        order = find_order(state, order_id)
        if order and action == "mark_delivery":
            payment_collected = request.POST.get("delivery_result") == "yes"
            mark_delivery(order, payment_collected)
            save_prototype_state(request, state)
            messages.success(request, "Estado de entrega actualizado.")
            return redirect("pagos:prototype_conductor")

    return render(request, "pagos/prototipo_conductor.html", {"orders": orders, "state": state})


def gestion_pagos(request):
    pedidos = Pedido.objects.select_related("cliente__usuario").prefetch_related("pagos_pedido").all()

    if request.method == "POST":
        pago_id = request.POST.get("pago_id")
        accion = request.POST.get("accion")
        pago = PagoPedido.objects.filter(id_pago_pedido=pago_id).first()
        if pago and accion in ["aprobar", "rechazar"]:
            if accion == "aprobar":
                pago.estado_pago = "pago aprobado"
                pago.save(update_fields=["estado_pago"])
                messages.success(request, "Pago aprobado correctamente.")
            else:
                pago.estado_pago = "pago rechazado"
                pago.motivo_rechazo = request.POST.get("motivo_rechazo", "")
                pago.save(update_fields=["estado_pago", "motivo_rechazo"])
                messages.warning(request, "Pago rechazado.")
        return redirect("pagos:gestion_pagos")

    db_missing_pagos_table = False
    try:
        for _ in pedidos[:1]:
            break
    except Exception:
        db_missing_pagos_table = True
        pedidos = []

    return render(request, "pagos/gestion_pagos.html", {"pedidos": pedidos, "db_missing_pagos_table": db_missing_pagos_table})
