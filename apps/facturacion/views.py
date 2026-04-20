from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.usuarios.views import admin_required
from .models import Factura, Pago
from django.db import transaction
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages

@admin_required
def lista_facturas(request):
    estado = request.GET.get('estado')
    q = request.GET.get('q')
    
    # JOIN con cliente y orden, prefetch de pagos
    qs = Factura.objects.select_related('cliente', 'orden').prefetch_related('pagos')
    
    if estado in ['pendiente', 'pagada', 'anulada']:
        qs = qs.filter(estado=estado)
    if q:
        qs = qs.filter(numero__icontains=q)
        
    return render(request, 'facturacion/lista.html', {
        'facturas': qs, 
        'estado': estado,
        'metodos_pago': Pago.METODOS
    })

@admin_required
@require_POST
def registrar_pago(request):
    factura_id = request.POST.get('factura_id')
    monto_str = request.POST.get('monto', '0')
    metodo = request.POST.get('metodo')
    
    try:
        monto = Decimal(monto_str)
    except:
        return JsonResponse({'error': 'Monto inválido'}, status=400)
        
    if monto <= 0 or metodo not in dict(Pago.METODOS):
        return JsonResponse({'error': 'Datos de pago inválidos'}, status=400)
        
    try:
        with transaction.atomic():
            factura = Factura.objects.select_for_update().get(id=factura_id)
            if factura.estado == 'anulada':
                return JsonResponse({'error': 'La factura está anulada'}, status=400)
            if factura.estado == 'pagada':
                return JsonResponse({'error': 'La factura ya ha sido pagada totalmente'}, status=400)
                
            Pago.objects.create(
                factura=factura, 
                monto=monto, 
                metodo=metodo,
                referencia=request.POST.get('referencia', ''),
                registrado_por=request.user
            )
            
            # Recalcular saldo
            pagado = sum(p.monto for p in factura.pagos.all())
            if pagado >= factura.total:
                factura.estado = 'pagada'
                factura.save()
                
        return JsonResponse({'status': 'ok', 'estado': factura.get_estado_display()})
    except Factura.DoesNotExist:
        return JsonResponse({'error': 'Factura no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
