from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from ordenes.models import Orden

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Sum, Q
from django.utils.timezone import now
from django.contrib import messages
from django.http import JsonResponse


# ---------------- REGISTRO ----------------
def registro(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        username = request.POST.get("usuario")
        email = request.POST.get("correo")
        telefono = request.POST.get("telefono")
        tipo_documento = request.POST.get("tipo_documento")
        documento = request.POST.get("documento")
        rol = request.POST.get("rol")
        password = request.POST.get("contrasena")
        confirmar = request.POST.get("confirmar_contrasena")

        if password != confirmar:
            return render(request, "usuarios/registro.html", {
                "error": "Las contraseñas no coinciden"
            })

        if User.objects.filter(username=username).exists():
            return render(request, "usuarios/registro.html", {
                "error": "Este nombre de usuario ya está registrado"
            })

        if User.objects.filter(email=email).exists():
            return render(request, "usuarios/registro.html", {
                "error": "Este correo ya está registrado"
            })

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        Usuario.objects.create(
            user=user,
            nombre=nombre,
            telefono=telefono,
            rol=rol,
            tipo_documento=tipo_documento,
            documento=documento
        )

        return redirect("usuarios:login")

    return render(request, "usuarios/registro.html")


def login_usuario(request):
    if request.method == "POST":
        identifier = request.POST.get("username")
        password = request.POST.get("password")

        # Intentar autenticar por username
        user = authenticate(request, username=identifier, password=password)

        # Si falla, intentar buscar por correo
        if user is None:
            try:
                user_obj = User.objects.get(email=identifier)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None

        if user is not None:
            login(request, user)
            
            # Si es superusuario, creamos el perfil si no existe y entramos
            if user.is_superuser:
                Usuario.objects.get_or_create(
                    user=user,
                    defaults={'nombre': user.username, 'rol': 'admin'}
                )
                return redirect("usuarios:panel")

            # Para usuarios normales, verificamos el perfil usando filter() para evitar el error amarillo
            perfil = Usuario.objects.filter(user=user).first()
            if perfil:
                if perfil.rol == "admin":
                    return redirect("usuarios:panel")
                elif perfil.rol == "cliente":
                    return redirect("usuarios:panel_cliente")
                elif perfil.rol == "conductor":
                    return redirect("usuarios:panel_conductor")
                else:
                    return redirect("usuarios:panel")
            else:
                logout(request)
                return render(request, "usuarios/login.html", {
                    "error": "Tu cuenta no tiene un perfil asignado."
                })
        else:
            return render(request, "usuarios/login.html", {
                "error": "Usuario o contraseña incorrectos"
            })

    return render(request, "usuarios/login.html")


# ---------------- PANEL ADMIN ----------------
@login_required
def panel(request):
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        if request.user.is_superuser:
            usuario = Usuario.objects.create(
                user=request.user,
                nombre=request.user.username,
                rol='admin',
                estado='activo'
            )
        else:
            logout(request)
            return redirect("usuarios:login")

    if usuario.rol == "admin":
        context = {
            "pedidos_pendientes": Orden.objects.filter(estado="pendiente").count(),
            "conductores": Usuario.objects.filter(rol="conductor").count(),
            "entregas_hoy": Orden.objects.filter(
                estado="entregado",
                fecha__date=now().date()
            ).count(),
            "clientes": Usuario.objects.filter(rol="cliente").count(),
            "pedidos_recientes": Orden.objects.all().order_by("-fecha")[:5]
        }
        return render(request, "dashboard/panel-admin.html", context)
    return redirect("usuarios:login")


# ---------------- CONDUCTOR ----------------
@login_required
def panel_conductor(request):
    try:
        conductor = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")
        
    pedidos = Orden.objects.filter(conductor=conductor)
    return render(request, "usuarios/panel-conductor.html", {
        "pedidos": pedidos
    })


@login_required
def pedidos_conductor(request):
    conductor = request.user.usuario
    pedidos = Orden.objects.filter(
        conductor=conductor
    ).exclude(estado="entregado")
    return render(request, "usuarios/pedidos_conductor.html", {
        "pedidos": pedidos
    })


@login_required
def mis_entregas(request):
    conductor = request.user.usuario
    entregas = Orden.objects.filter(
        conductor=conductor,
        estado="entregado"
    ).order_by("-fecha")
    return render(request, "usuarios/mis-entregas.html", {
        "entregas": entregas
    })


# ---------------- CLIENTE ----------------
@login_required
def panel_cliente(request):
    try:
        cliente = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")
        
    pedidos = Orden.objects.filter(cliente=cliente)
    context = {
        "pedidos_activos": pedidos.filter(estado="pendiente").count(),
        "entregadas": pedidos.filter(estado="entregado").count(),
        "total_gastado": pedidos.aggregate(total=Sum("precio"))["total"] or 0,
        "ultimos_pedidos": pedidos.order_by("-fecha")[:5]
    }
    return render(request, "cliente/dashboard.html", context)


@login_required
def mis_pedidos(request):
    cliente = request.user.usuario
    pedidos = Orden.objects.filter(
        cliente=cliente
    ).order_by("-fecha")
    return render(request, "cliente/mis_pedidos.html", {
        "pedidos": pedidos
    })


@login_required
def perfil_cliente(request):
    cliente = request.user.usuario
    return render(request, "cliente/perfil.html", {
        "cliente": cliente
    })


@login_required
def seguimiento_pedidos(request):
    cliente = request.user.usuario
    pedidos = Orden.objects.filter(cliente=cliente).order_by("-fecha")
    return render(request, "cliente/seguimiento.html", {
        "pedidos": pedidos
    })


@login_required
def historial_pedidos(request):
    cliente = request.user.usuario
    pedidos = Orden.objects.filter(
        cliente=cliente, 
        estado="entregado"
    ).order_by("-fecha")
    return render(request, "cliente/historial.html", {
        "pedidos": pedidos
    })


# ---------------- GESTIÓN DE USUARIOS ----------------
@login_required
def crear_usuario(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        email = request.POST.get("email")
        password = request.POST.get("password")
        telefono = request.POST.get("telefono")
        rol = request.POST.get("rol")
        tipo_doc = request.POST.get("tipo_doc")
        documento = request.POST.get("documento")

        # Crear User de Django
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )

        # Crear Perfil Usuario
        Usuario.objects.create(
            user=user,
            nombre=nombre,
            telefono=telefono,
            rol=rol,
            tipo_documento=tipo_doc,
            documento=documento
        )

        return redirect("usuarios:lista_usuarios")

    return redirect("usuarios:lista_usuarios")

@login_required
def lista_usuarios(request):
    usuarios = Usuario.objects.filter(rol='cliente')
    return render(request, "dashboard/usuarios_lista.html", {"usuarios": usuarios})


@login_required
def eliminar_usuario(request, id):
    usuario_obj = get_object_or_404(Usuario, id=id) 
    usuario_obj.delete()
    return redirect("usuarios:lista_usuarios")


@login_required
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre")
        usuario.telefono = request.POST.get("telefono")
        usuario.rol = request.POST.get("rol")
        usuario.save()
        return redirect("usuarios:lista_usuarios")
    return render(request, "dashboard/editar_usuario.html", {
        "usuario": usuario
    })


@login_required
def lista_conductores(request):
    conductores = Usuario.objects.filter(rol="conductor")
    return render(request, "dashboard/conductores_lista.html", {
        "conductores": conductores
    })


@login_required
def perfil_conductor(request):
    conductor_id = request.GET.get('id')
    if conductor_id and request.user.usuario.rol == 'admin':
        conductor = get_object_or_404(Usuario, id=conductor_id)
    else:
        conductor = request.user.usuario
        
    pedidos = Orden.objects.filter(conductor=conductor)
    return render(request, "usuarios/perfil-conductor.html", {
        "conductor": conductor,
        "pedidos": pedidos
    })


# ---------------- GESTIÓN DE VEHÍCULOS ----------------
@login_required
def lista_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    return render(request, "dashboard/vehiculos_lista.html", {
        "vehiculos": vehiculos
    })


@login_required
def crear_vehiculo(request):
    if request.method == "POST":
        Vehiculo.objects.create(
            placa=request.POST.get("placa"),
            tipo=request.POST.get("tipo"),
            capacidad=request.POST.get("capacidad"),
            estado="disponible"
        )
        return redirect("usuarios:lista_vehiculos")
    return render(request, "dashboard/vehiculo_crear.html")


# ---------------- GESTIÓN DE MATERIALES ----------------
@login_required
def materiales_lista(request):
    query = request.GET.get('q')
    if query:
        materiales = Material.objects.filter(
            Q(nombre__icontains=query) | 
            Q(descripcion__icontains=query) |
            Q(tipo__icontains=query)
        )
    else:
        materiales = Material.objects.all()
    
    return render(request, "dashboard/materiales_lista.html", {
        "materiales": materiales
    })


@login_required
def api_materiales(request):
    materiales = Material.objects.all().values('id', 'nombre', 'precio', 'stock', 'tipo')
    return JsonResponse(list(materiales), safe=False)


@login_required
def crear_material(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        descripcion = request.POST.get("descripcion")
        tipo = request.POST.get("tipo")
        precio = request.POST.get("precio")
        stock = request.POST.get("stock")

        Material.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            tipo=tipo,
            precio=precio,
            stock=stock
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "success", "message": "Material creado correctamente"})
            
        messages.success(request, "Material creado correctamente")
        return redirect("usuarios:materiales_lista")
    
    return render(request, "dashboard/material_crear.html")


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
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "success", "message": "Material actualizado"})
            
        messages.success(request, "Material actualizado")
        return redirect("usuarios:materiales_lista")
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            "id": material.id,
            "nombre": material.nombre,
            "descripcion": material.descripcion,
            "tipo": material.tipo,
            "precio": str(material.precio),
            "stock": material.stock
        })
        
    return render(request, "dashboard/material_editar.html", {"material": material})


@login_required
def eliminar_material(request, id):
    material = get_object_or_404(Material, id=id)
    if request.method == "POST":
        material.delete()
        messages.success(request, "Material eliminado correctamente")
    return redirect("usuarios:materiales_lista")


# ---------------- REPORTES ----------------
@login_required
def reportes_admin(request):
    context = {
        "total": Orden.objects.count(),
        "pendientes": Orden.objects.filter(estado="pendiente").count(),
        "en_ruta": Orden.objects.filter(estado="en_ruta").count(),
        "entregadas": Orden.objects.filter(estado="entregado").count(),
    }
    return render(request, "dashboard/reportes.html", context)


# ---------------- PEDIDOS CLIENTE ----------------
@login_required
def crear_pedido(request):
    cliente = request.user.usuario
    materiales = Material.objects.all()

    if request.method == "POST":
        material_id = request.POST.get("material")
        cantidad_str = request.POST.get("cantidad")
        direccion = request.POST.get("direccion")

        if not material_id or not cantidad_str or not direccion:
            return render(request, "cliente/crear_pedido.html", {
                "materiales": materiales,
                "error": "Por favor, completa todos los campos."
            })

        try:
            material = get_object_or_404(Material, id=material_id)
            cantidad = int(cantidad_str)
            total = material.precio * cantidad

            nueva_orden = Orden.objects.create(
                cliente=cliente,
                material=material,
                cantidad=cantidad,
                direccion_origen="Bodega Central",
                direccion_destino=direccion,
                precio=total,
                estado="pendiente"
            )
            
            return redirect("usuarios:mis_pedidos")

        except Exception as e:
            return render(request, "cliente/crear_pedido.html", {
                "materiales": materiales,
                "error": f"Error interno: {e}"
            })

    return render(request, "cliente/crear_pedido.html", {
        "materiales": materiales
    })


# ---------------- GESTIÓN DE PEDIDOS ADMIN ----------------
@login_required
def lista_pedidos_admin(request):
    pedidos = Orden.objects.all().order_by("-fecha")
    return render(request, "dashboard/pedidos_lista.html", {
        "pedidos": pedidos
    })


@login_required
def ver_pedido_admin(request, id):
    pedido = get_object_or_404(Orden, id=id)
    return render(request, "dashboard/pedido_detalle.html", {
        "pedido": pedido
    })


@login_required
def eliminar_orden(request, id):
    orden = get_object_or_404(Orden, id=id)
    orden.delete()
    return redirect("ordenes:lista_ordenes")


# ---------------- LOGOUT ----------------
def cerrar_sesion(request):
    logout(request)
    return redirect("usuarios:login")
