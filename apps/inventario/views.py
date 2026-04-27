from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.usuarios.views import admin_required
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from apps.usuarios.models import Material, Stock
from apps.historial.utils import registrar_actividad
from django.db import transaction
from django.views.decorators.http import require_POST
from .models import MovimientoInventario

# HU-17
@admin_required
@require_POST
def registrar_entrada(request):
    material_id = request.POST.get('material_id')
    cantidad = int(request.POST.get('cantidad', 0))
    if cantidad <= 0:
        return JsonResponse({'error': 'Cantidad debe ser > 0'}, status=400)
    try:
        with transaction.atomic():
            material = Material.objects.select_for_update().get(id=material_id)
            stock, _ = Stock.objects.select_for_update().get_or_create(material=material)
            stock.cantidad += cantidad
            stock.save()
            MovimientoInventario.objects.create(
                material=material,
                tipo='entrada',
                cantidad=cantidad,
                motivo=request.POST.get('motivo', 'entrada manual'),
                usuario=request.user
            )
        return JsonResponse({'status': 'ok', 'stock': stock.cantidad})
    except Material.DoesNotExist:
        return JsonResponse({'error': 'Material no existe'}, status=404)

@admin_required
def movimientos_lista(request):
    movimientos = MovimientoInventario.objects.all().select_related('material', 'usuario')
    materiales = Material.objects.all().order_by('nombre')
    return render(request, "inventario/movimientos.html", {
        "movimientos": movimientos,
        "materiales": materiales
    })

def buscar_materiales(query=None):
    """
    Lógica unificada para buscar materiales por nombre, descripción o tipo.
    Optimizado con select_related('stock_info') para evitar N+1 al consultar stock.
    """
    materiales = Material.objects.all().select_related('stock_info')
    if query:
        materiales = materiales.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query) |
            Q(tipo__icontains=query)
        )
    return materiales

@admin_required
def stock_lista(request):
    q = request.GET.get('q')
    stocks = Stock.objects.all().select_related('material')
    
    if q:
        stocks = stocks.filter(
            Q(material__nombre__icontains=q) |
            Q(ubicacion__icontains=q) |
            Q(material__tipo__icontains=q)
        )
        
    return render(request, "inventario/stock.html", {
        "stocks": stocks,
        "query": q
    })

@admin_required
def editar_stock(request, id):
    stock = get_object_or_404(Stock, id=id)
    if request.method == "POST":
        stock.cantidad = request.POST.get("cantidad")
        stock.ubicacion = request.POST.get("ubicacion")
        stock.save()
        messages.success(request, f"Stock de {stock.material.nombre} actualizado.")
        return redirect("inventario:stock_lista")
    return render(request, "inventario/form_stock.html", {"stock": stock})

@admin_required
def materiales_lista(request):
    query = request.GET.get('q')
    tipo = request.GET.get('tipo')
    
    materiales = buscar_materiales(query)
    if tipo:
        materiales = materiales.filter(tipo=tipo)
    
    return render(request, "inventario/lista.html", {
        "materiales": materiales,
        "query": query,
        "tipo_actual": tipo
    })

@admin_required
def api_materiales(request):
    materiales = Material.objects.filter(stock_info__cantidad__gt=0).select_related('stock_info')
    data = []
    for m in materiales:
        data.append({
            'id': m.id,
            'nombre': m.nombre,
            'precio': float(m.precio),
            'stock': m.stock,
            'tipo': m.tipo
        })
    return JsonResponse(data, safe=False)

from apps.usuarios.forms import MaterialForm
from apps.usuarios.views import admin_required

@admin_required
def crear_material(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            try:
                material = form.save()
                # El Stock se crea vía signals en apps.usuarios.signals
                registrar_actividad(request, 'crear', 'inventario', material.id, f"Material creado: {material.nombre}")
                
                success_msg = "Material creado correctamente."
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    messages.success(request, success_msg)
                    return JsonResponse({"status": "success", "message": success_msg})
                
                messages.success(request, success_msg)
                return redirect("inventario:materiales_lista")
            except Exception as e:
                error_msg = f"Error al crear material: {str(e)}"
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"status": "error", "message": error_msg}, status=500)
                messages.error(request, error_msg)
    else:
        form = MaterialForm()

    return render(request, "inventario/form.html", {"form": form, "action": "crear"})

@admin_required
def editar_material(request, id):
    material = get_object_or_404(Material, id=id)
    if request.method == "POST":
        form = MaterialForm(request.POST, instance=material)
        if form.is_valid():
            form.save()
            registrar_actividad(request, 'editar', 'inventario', material.id, f"Material editado: {material.nombre}")
            messages.success(request, "Material actualizado correctamente.")
            return redirect("inventario:materiales_lista")
    else:
        form = MaterialForm(instance=material)
    return render(request, "inventario/form.html", {"form": form, "action": "editar"})

@admin_required
def eliminar_material(request, id):
    material = get_object_or_404(Material, id=id)
    
    # Validaciones antes de eliminar
    if material.stock > 0:
        messages.error(request, f"No se puede eliminar {material.nombre} porque aún tiene stock disponible ({material.stock}).")
        return redirect("inventario:materiales_lista")
        
    if material.detalles.exists(): # Detalles de orden
        messages.error(request, f"No se puede eliminar {material.nombre} porque está asociado a pedidos existentes.")
        return redirect("inventario:materiales_lista")

    nombre = material.nombre
    material.delete()
    registrar_actividad(request, 'eliminar', 'inventario', id, f"Material eliminado: {nombre}")
    messages.success(request, f"Material {nombre} eliminado correctamente.")
    return redirect("inventario:materiales_lista")
