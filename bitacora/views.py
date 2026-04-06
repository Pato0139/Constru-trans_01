from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Bitacora

@login_required
def lista_bitacora(request):
    if not request.user.is_superuser and request.user.usuario.rol != 'admin':
        return render(request, "403.html", status=403)
        
    registros = Bitacora.objects.all().order_by('-fecha_hora')
    
    # Filtros
    usuario_q = request.GET.get('usuario')
    accion_q = request.GET.get('accion')
    modulo_q = request.GET.get('modulo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    if usuario_q:
        registros = registros.filter(usuario__username__icontains=usuario_q)
    if accion_q:
        registros = registros.filter(accion=accion_q)
    if modulo_q:
        registros = registros.filter(modulo=modulo_q)
    if fecha_inicio:
        registros = registros.filter(fecha_hora__date__gte=fecha_inicio)
    if fecha_fin:
        registros = registros.filter(fecha_hora__date__lte=fecha_fin)
        
    context = {
        'registros': registros,
        'acciones': Bitacora.ACCIONES,
        'modulos': Bitacora.objects.values_list('modulo', flat=True).distinct(),
        'filtros': {
            'usuario': usuario_q,
            'accion': accion_q,
            'modulo': modulo_q,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
    }
    
    return render(request, "bitacora/lista.html", context)
