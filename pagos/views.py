from django.db.models import Q
from django.shortcuts import render

from usuarios.models import MetodoPago
from usuarios.views import admin_required

from .models import Pago


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
