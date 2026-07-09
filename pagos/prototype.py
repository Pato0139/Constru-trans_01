import re
from datetime import datetime


TAX_RATE = 0.19


def calculate_order_totals(items):
    subtotal = sum(int(item.get("quantity", 0)) * int(item.get("unit_price", 0)) for item in items)
    iva = int(round(subtotal * TAX_RATE))
    total = subtotal + iva
    return {
        "subtotal": subtotal,
        "iva": iva,
        "total": total,
    }


def generate_order_code(existing_orders):
    if not existing_orders:
        return "PED-000001"

    numbers = []
    for order in existing_orders:
        match = re.search(r"(\d+)$", str(order.get("id", "")))
        if match:
            numbers.append(int(match.group(1)))

    next_number = max(numbers) + 1 if numbers else len(existing_orders) + 1
    return f"PED-{next_number:06d}"


def append_history_entry(order, text):
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
    history = order.setdefault("history", [])
    history.append({"timestamp": timestamp, "text": text})
    return history


def update_payment_and_order_status(order, new_status):
    order["payment_status"] = new_status

    mapping = {
        "Pendiente": "Pendiente de pago",
        "Comprobante enviado": "Pendiente de revisión",
        "En revisión": "Pendiente de revisión",
        "Pago aprobado": "Autorizado para despacho",
        "Pago rechazado": "Pendiente de revisión",
        "Contra entrega": "Pendiente de pago",
        "Pago recibido": "Entregado",
    }

    order["order_status"] = mapping.get(new_status, order.get("order_status", "Pendiente de pago"))
    append_history_entry(order, f"{new_status}.")
    return order


def assign_transport(order, vehicle, driver, transport_date, transport_time, notes):
    order["assigned_vehicle"] = vehicle
    order["assigned_driver"] = driver
    order["transport_date"] = transport_date
    order["transport_time"] = transport_time
    order["transport_notes"] = notes
    order["order_status"] = "Vehículo asignado"
    append_history_entry(order, "Vehículo asignado.")
    append_history_entry(order, "Conductor asignado.")
    return order


def mark_delivery(order, payment_collected):
    if payment_collected:
        order["payment_status"] = "Pago recibido"
        order["order_status"] = "Entregado"
        append_history_entry(order, "Pedido entregado.")
        append_history_entry(order, "Pago recibido.")
    else:
        order["payment_status"] = "Pendiente"
        order["order_status"] = "Incidencia de pago"
        append_history_entry(order, "Incidencia de pago.")
        append_history_entry(order, "Notificación enviada al administrador.")
    return order


def build_demo_order():
    return {
        "id": "PED-000154",
        "customer": "Laura Pérez",
        "phone": "3004567890",
        "materials": [
            {"name": "Cemento", "quantity": 20, "unit": "sacos", "unit_price": 45000},
            {"name": "Varilla", "quantity": 5, "unit": "rollos", "unit_price": 120000},
        ],
        "delivery_address": "Calle 80 # 45-12, Bogotá",
        "delivery_date": "2026-07-12",
        "observations": "Entrega en horario de la mañana.",
        "subtotal": 0,
        "iva": 0,
        "total": 0,
        "payment_method": "Transferencia Bancolombia",
        "payment_status": "En revisión",
        "order_status": "Pendiente de revisión",
        "proof": {
            "name": "transferencia.pdf",
            "size": "2.1 MB",
            "type": "application/pdf",
        },
        "rejection_reason": None,
        "assigned_vehicle": "Camión 7T",
        "assigned_driver": "Carlos Morales",
        "transport_date": None,
        "transport_time": None,
        "transport_notes": None,
        "history": [
            {"timestamp": "08/07/2026 09:15", "text": "Pedido creado."},
            {"timestamp": "08/07/2026 09:16", "text": "Método de pago seleccionado."},
            {"timestamp": "08/07/2026 09:17", "text": "Comprobante cargado."},
        ],
    }


def seed_demo_state(state):
    if not state.get("orders"):
        demo_order = build_demo_order()
        totals = calculate_order_totals(demo_order["materials"])
        demo_order["subtotal"] = totals["subtotal"]
        demo_order["iva"] = totals["iva"]
        demo_order["total"] = totals["total"]
        state["orders"] = [demo_order]
        state["active_order_id"] = demo_order["id"]
        state["role"] = "cliente"
    return state
