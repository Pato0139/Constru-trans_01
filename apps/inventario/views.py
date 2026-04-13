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
    """
    materiales = Material.objects.all()
    if query:
        materiales = materiales.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query) |
            Q(tipo__icontains=query)
        )
    return materiales

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
    materiales = Material.objects.all().values('id', 'nombre', 'precio', 'stock', 'tipo')
    return JsonResponse(list(materiales), safe=False)

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
        stock = request.POST.get("stock")

        if not all([nombre, tipo, precio, stock]):
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
                precio=precio,
                stock=stock
            )
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
        material.stock = request.POST.get("stock")
        material.save()
        registrar_actividad(request, 'editar', 'inventario', material.id, f"Material editado: {material.nombre}")
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            messages.success(request, "Material actualizado correctamente.")
            return JsonResponse({"status": "success"})
            
        messages.success(request, "Material actualizado")
        return redirect("inventario:materiales_lista")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            "id": material.id,
            "nombre": material.nombre,
            "descripcion": material.descripcion,
            "tipo": material.tipo,
            "precio": str(material.precio),
            "stock": material.stock
        })
        
    return render(request, "inventario/form.html", {"material": material, "action": "editar"})

@login_required
def eliminar_material(request, id):
    material = get_object_or_404(Material, id=id)
    material.delete()
    messages.success(request, "Material eliminado correctamente")
    return redirect("inventario:materiales_lista")
