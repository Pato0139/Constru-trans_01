from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Orden, Entrega
from usuarios.models import Usuario, Vehiculo
from django.shortcuts import redirect


# 📋 LISTAR ÓRDENES
@login_required
def lista_ordenes(request):

    ordenes = Orden.objects.all().order_by("-fecha")

    return render(request, "ordenes/lista_ordenes.html", {
        "ordenes": ordenes
    })


@login_required
def crear_orden(request):
    cliente = request.user.usuario
    materiales = Material.objects.all()

    if request.method == "POST":
        # 1. Capturar datos asegurando que los nombres coincidan con el HTML
        material_id = request.POST.get("material")
        cantidad_str = request.POST.get("cantidad")
        direccion = request.POST.get("direccion")

        # LOG de depuración (Mira tu terminal negra donde corre el server)
        print(f"--- INTENTO DE ORDEN ---")
        print(f"ID Material: {material_id} | Cantidad: {cantidad_str} | Dirección: {direccion}")

        if not material_id or not cantidad_str or not direccion:
            print("ERROR: Faltan campos en el formulario")
            return render(request, "cliente/crear_pedido.html", {
                "materiales": materiales,
                "error": "Por favor, completa todos los campos."
            })

        try:
            # 2. Procesar datos
            material = get_object_or_404(Material, id=material_id)
            cantidad = int(cantidad_str)
            total = material.precio * cantidad

            # 3. Crear el objeto en la base de datos
            # IMPORTANTE: Revisa que estos nombres de campo (cliente, precio, etc) 
            # sean EXACTOS a los de tu models.py en la carpeta 'ordenes'
            nueva_orden = Orden.objects.create(
                cliente=cliente,
                direccion_origen="Bodega Central",
                direccion_destino=direccion,
                precio=total,
                estado="pendiente"
            )
            
            print(f"ÉXITO: Orden #{nueva_orden.id} creada correctamente.")
            return redirect("mis_pedidos")

        except Exception as e:
            # Si el código llega aquí, imprime el error real (ej: campo no existe)
            print(f"ERROR CRÍTICO AL GUARDAR: {e}")
            return render(request, "cliente/crear_pedido.html", {
                "materiales": materiales,
                "error": f"Error interno: {e}"
            })

    return render(request, "cliente/crear_pedido.html", {
        "materiales": materiales
    })

# 🚚 CREAR ENTREGA AUTOMÁTICA (SIN HTML)
def crear_entrega(request, orden_id):
    orden = Orden.objects.get(id=orden_id)

    conductores = Usuario.objects.filter(rol="conductor")
    vehiculos = Vehiculo.objects.all()

    if request.method == "POST":
        conductor_id = request.POST.get("conductor")
        vehiculo_id = request.POST.get("vehiculo")

        Entrega.objects.create(
            pedido=orden,
            conductor_id=conductor_id,
            vehiculo_id=vehiculo_id,
            fecha=orden.fecha
        )

        orden.estado = "en_ruta"
        orden.conductor_id = conductor_id
        orden.save()

        return redirect("lista_ordenes")

    return render(request, "ordenes/asignar_entrega.html", {
        "orden": orden,
        "conductores": conductores,
        "vehiculos": vehiculos
    })
    return redirect("lista_ordenes")
def editar_orden(request, orden_id):
    pass #

def eliminar_orden(request, orden_id):
    return redirect('lista_ordenes')