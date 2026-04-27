from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.usuarios.views import admin_required
from .models import Factura
from apps.pagos.models import Pago
from django.db import transaction
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from decimal import Decimal
from django.contrib import messages

# HU-37
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

@login_required
def mis_facturas(request):
    cliente = request.user.usuario
    facturas = Factura.objects.filter(cliente=cliente).select_related('orden').prefetch_related('pagos')
    
    return render(request, 'facturacion/mis_facturas.html', {
        'facturas': facturas,
        'metodos_pago': Pago.METODOS
    })

# HU-38
@login_required
@require_POST
def registrar_pago(request):
    factura_id = request.POST.get('factura_id')
    monto_str = request.POST.get('monto', '0')
    metodo = request.POST.get('metodo')
    
    # VALIDACIÓN: Monto numérico
    try:
        monto = Decimal(monto_str)
    except:
        return JsonResponse({'error': 'Monto inválido'}, status=400)
        
    # VALIDACIÓN: cantidad > 0
    if monto <= 0:
        return JsonResponse({'error': 'El monto debe ser mayor a cero'}, status=400)
    
    if metodo not in dict(Pago.METODOS):
        return JsonResponse({'error': 'Método de pago inválido'}, status=400)
        
    try:
        # TRANSACCIÓN ATÓMICA: o todo o nada
        with transaction.atomic():
            # Bloqueamos la factura para evitar pagos duplicados concurrentes
            factura = Factura.objects.select_for_update().get(id=factura_id)
            
            # Seguridad: Solo admin o el dueño pueden pagar
            if request.user.usuario.rol != 'admin' and factura.cliente != request.user.usuario:
                return JsonResponse({'error': 'No autorizado'}, status=403)

            if factura.estado == 'anulada':
                return JsonResponse({'error': 'La factura está anulada'}, status=400)
            if factura.estado == 'pagada':
                return JsonResponse({'error': 'La factura ya ha sido pagada totalmente'}, status=400)
            
            # VALIDACIÓN: No exceder saldo
            if monto > factura.saldo_pendiente:
                return JsonResponse({'error': f'El monto excede el saldo pendiente (${factura.saldo_pendiente})'}, status=400)
                
            # REGISTRAR PAGO
            Pago.objects.create(
                factura=factura, 
                monto=monto, 
                metodo=metodo,
                referencia=request.POST.get('referencia', 'Pago realizado por cliente' if request.user.usuario.rol != 'admin' else ''),
                registrado_por=request.user
            )
            
            # ACTUALIZAR ESTADO SI SE COMPLETA EL PAGO
            if factura.saldo_pendiente <= 0:
                factura.estado = 'pagada'
                factura.save()
                mensaje_adicional = "Factura pagada por completo."
            else:
                mensaje_adicional = f"Pago parcial registrado. Monto por pagar: ${factura.saldo_pendiente}"
                
        return JsonResponse({
            'status': 'ok', 
            'estado': factura.get_estado_display(),
            'mensaje': mensaje_adicional,
            'saldo': float(factura.saldo_pendiente)
        })
    except Factura.DoesNotExist:
        return JsonResponse({'error': 'Factura no encontrada'}, status=404)
@admin_required
def anular_factura(request, id):
    factura = get_object_or_404(Factura, id=id)
    if factura.estado == 'pagada':
        return JsonResponse({'error': 'No se puede anular una factura ya pagada'}, status=400)
    
    factura.estado = 'anulada'
    factura.save()
    return JsonResponse({'status': 'ok', 'mensaje': 'Factura anulada correctamente'})

@admin_required
def editar_factura_monto(request, id):
    factura = get_object_or_404(Factura, id=id)
    if factura.estado != 'pendiente':
        return JsonResponse({'error': 'Solo se pueden editar facturas en estado pendiente'}, status=400)
    
    try:
        nuevo_monto = Decimal(request.POST.get('monto'))
        if nuevo_monto <= 0:
            raise ValueError
        
        factura.subtotal = nuevo_monto / Decimal('1.19')
        factura.iva = nuevo_monto - factura.subtotal
        factura.total = nuevo_monto
        factura.save()
        
        # También actualizar el precio de la orden para que coincida
        if factura.orden:
            factura.orden.precio = nuevo_monto
            factura.orden.save()
            
        return JsonResponse({'status': 'ok', 'mensaje': 'Monto de factura actualizado'})
    except:
        return JsonResponse({'error': 'Monto inválido'}, status=400)
