from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages
from django.http import JsonResponse
from apps.usuarios.models import Material
from historial.utils import registrar_actividad

def buscar_materiales(query=None):
    """
    Lógica unificada para buscar materiales por nombre, descripción o tipo.
    Solo muestra materiales activos.
    """
    materiales = Material.objects.filter(activo=True)
    if query:
        materiales = materiales.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query) |
            Q(tipo__icontains=query)
        )
    return materiales

@login_required
def api_materiales_stock(request):
    """
    Endpoint para listar materiales con stock disponible en formato JSON.
    Soporta filtrado opcional por 'min_stock' vía GET.
    """
    try:
        # 1. Obtener parámetro de filtro opcional
        min_stock = request.GET.get('min_stock', 0)
        
        # Validar que sea un número
        try:
            min_stock = int(min_stock)
        except ValueError:
            return JsonResponse({
                "status": "error",
                "message": "El parámetro 'min_stock' debe ser un número entero."
            }, status=400)

        # 2. Consultar datos del modelo Material (Solo activos y con stock >= min_stock)
        materiales = Material.objects.filter(
            activo=True, 
            stock_actual__gte=min_stock
        ).order_by('nombre')

        # 3. Verificar si hay datos
        if not materiales.exists():
            return JsonResponse({
                "status": "success",
                "count": 0,
                "data": [],
                "message": "No se encontraron materiales con el stock solicitado."
            }, status=200)

        # 4. Estructurar la respuesta JSON
        data = []
        for m in materiales:
            data.append({
                "id": m.id,
                "nombre": m.nombre,
                "tipo": m.tipo,
                "descripcion": m.descripcion,
                "precio": float(m.precio),
                "stock": m.stock_actual,
                "moneda": "COP"
            })

        return JsonResponse({
            "status": "success",
            "count": len(data),
            "data": data
        }, safe=False, status=200)

    except Exception as e:
        # Manejo de errores inesperados
        return JsonResponse({
            "status": "error",
            "message": f"Ocurrió un error inesperado: {str(e)}"
        }, status=500)

@login_required
def materiales_lista(request):
    query = request.GET.get('q')
    materiales = buscar_materiales(query)
    
    return render(request, "inventario/lista.html", {
        "materiales": materiales,
        "query": query
    })

@login_required
def api_materiales(request):
    materiales = Material.objects.all().select_related('stock')
    data = []
    for m in materiales:
        data.append({
            'id': m.id,
            'nombre': m.nombre,
            'precio': str(m.precio),
            'stock_actual': m.stock.cantidad_actual if hasattr(m, 'stock') else 0,
            'tipo': m.tipo
        })
    return JsonResponse(data, safe=False)

@login_required
def crear_material(request):
    if request.user.usuario.rol != 'admin':
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("usuarios:panel")

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        tipo = request.POST.get("tipo")
        descripcion = request.POST.get("descripcion")
        precio = request.POST.get("precio")
        stock_actual = request.POST.get("stock")

        if not all([nombre, tipo, precio, stock_actual]):
            error_msg = "Los campos Nombre, Tipo, Precio y Stock son obligatorios."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            return render(request, "inventario/form.html", {"material": request.POST, "action": "crear"})

        try:
            material = Material.objects.create(
                nombre=nombre,
                tipo=tipo,
                descripcion=descripcion,
                precio=precio
            )
            # El stock se crea por señal, ahora lo actualizamos
            stock_obj = material.stock
            stock_obj.cantidad_actual = int(stock_actual)
            stock_obj.save()
            
            registrar_actividad(request, 'crear', 'inventario', material.id, f"Material creado: {nombre}")
            
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
            return render(request, "inventario/form.html", {
                "error": error_msg,
                "material": request.POST,
                "action": "crear"
            })

    return render(request, "inventario/form.html", {"action": "crear"})

@login_required
def editar_material(request, id):
    material = get_object_or_404(Material, id=id)
    if request.method == "POST":
        material.nombre = request.POST.get("nombre")
        material.descripcion = request.POST.get("descripcion")
        material.tipo = request.POST.get("tipo")
        material.precio = request.POST.get("precio")
        material.save()
        
        # Actualizar stock
        stock_obj, _ = StockMaterial.objects.get_or_create(material=material)
        stock_obj.cantidad_actual = int(request.POST.get("stock", 0))
        stock_obj.save()
        
        registrar_actividad(request, 'editar', 'inventario', material.id, f"Material editado: {material.nombre}")
        
        success_msg = "Material actualizado correctamente."
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            messages.success(request, success_msg)
            return JsonResponse({"status": "success", "message": success_msg})
        
        messages.success(request, success_msg)
        return redirect("inventario:materiales_lista")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        stock_obj, _ = StockMaterial.objects.get_or_create(material=material)
        return JsonResponse({
            "id": material.id,
            "nombre": material.nombre,
            "descripcion": material.descripcion,
            "tipo": material.tipo,
            "precio": str(material.precio),
            "stock": stock_obj.cantidad_actual
        })

    return render(request, "inventario/form.html", {"material": material, "action": "editar"})

@login_required
def eliminar_material(request, id):
    material = get_object_or_404(Material, id=id)
    material.activo = False
    material.save()
    registrar_actividad(request, 'eliminar', 'inventario', id, f"Material deshabilitado: {material.nombre}")
    messages.success(request, f"Material '{material.nombre}' deshabilitado correctamente")
    return redirect("inventario:materiales_lista")
