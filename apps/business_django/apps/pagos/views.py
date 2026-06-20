from django.db.models import Q
from django.shortcuts import render

from apps.usuarios.models import MetodoPago
from apps.usuarios.views import admin_required

from .models import Pago


@admin_required
def lista_pagos(request):
    q = request.GET.get('q', '')
    fecha = request.GET.get('fecha', '')
    metodo = request.GET.get('metodo', '')

    pagos = Pago.objects.select_related('factura', 'factura__cliente', 'registrado_por', 'codigo_metodo_pago').all().order_by('-fecha')

    if q:
        pagos = pagos.filter(
            Q(factura__numero__icontains=q) |
            Q(factura__cliente__nombres__icontains=q) |
            Q(factura__cliente__apellidos__icontains=q) |
            Q(referencia__icontains=q)
        )

    if fecha:
        pagos = pagos.filter(fecha__date=fecha)

    if metodo:
        pagos = pagos.filter(codigo_metodo_pago__codigo_metodo_pago=metodo)

    context = {
        'pagos': pagos,
        'q': q,
        'fecha': fecha,
        'metodo': metodo,
        'metodos_pago': MetodoPago.objects.all()
    }


    return render(request, 'pagos/lista.html', context)
