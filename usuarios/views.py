from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from ordenes.models import Orden

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Sum
from django.utils.timezone import now
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q


# ---------------- REGISTRO ----------------
def registro(request):

    if request.method == "POST":
        nombre = request.POST.get("nombre")
        email = request.POST.get("correo").strip().lower()
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

        if User.objects.filter(username=email).exists():
            return render(request, "usuarios/registro.html", {
                "error": "Este correo ya está registrado"
            })

        user = User.objects.create_user(
            username=email,
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

        return redirect("login")

    return render(request, "usuarios/registro.html")



def login_usuario(request):

    if request.method == "POST":
        username = request.POST.get("username").strip().lower()
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        # 🔥 DEBUG (aquí van los print)
        print("USER:", username)
        print("PASS:", password)
        print("AUTH:", user)

        if user is not None:
            login(request, user)

            if hasattr(user, "usuario"):
                rol = user.usuario.rol

                if rol == "admin":
                    return redirect("panel")
                elif rol == "cliente":
                    return redirect("panel_cliente")
                elif rol == "conductor":
                    return redirect("panel_conductor")

            return redirect("panel")

        else:
            return render(request, "usuarios/login.html", {
                "error": "Usuario o contraseña incorrectos"
            })

    return render(request, "usuarios/login.html")

# ---------------- PANEL ADMIN ----------------
@login_required
def panel(request):

    usuario = request.user.usuario

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

    return redirect("login")


# ---------------- CONDUCTOR ----------------
@login_required
def panel_conductor(request):
    conductor = request.user.usuario
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

    cliente = request.user.usuario
    pedidos = Orden.objects.filter(cliente=cliente)

    context = {
        "pedidos_activos": pedidos.filter(estado="pendiente").count(),
        "entregadas": pedidos.filter(estado="entregado").count(),
        "total_gastado": pedidos.aggregate(total=Sum("precio"))["total"] or 0,
        "ultimos_pedidos": pedidos.order_by("-fecha")[:5]
    }

    return render(request, "cliente/dashboard.html", context)


@login_required
def crear_pedido(request):
    cliente = request.user.usuario
    materiales = Material.objects.all()

    if request.method == "POST":
        material_id = request.POST.get("material")
        cantidad = request.POST.get("cantidad")
        direccion = request.POST.get("direccion")

        if not material_id or not cantidad or not direccion:
            return render(request, "cliente/crear_pedido.html", {
                "materiales": materiales,
                "error": "Todos los campos son obligatorios"
            })

        try:
            cantidad = int(cantidad)
            material = Material.objects.get(id=material_id)
        except:
            return render(request, "cliente/crear_pedido.html", {
                "materiales": materiales,
                "error": "Datos inválidos"
            })

        total = material.precio * cantidad

        Orden.objects.create(
            cliente=cliente,
            material=material,
            cantidad=cantidad,
            direccion_origen="Bodega",
            direccion_destino=direccion,
            precio=total,
            estado="pendiente"
        )

        return redirect("mis_pedidos")

    return render(request, "cliente/crear_pedido.html", {
        "materiales": materiales
    })


@login_required
def mis_pedidos(request):
    cliente = request.user.usuario

    pedidos = Orden.objects.filter(
        cliente=cliente
    ).order_by("-fecha")

    return render(request, "cliente/mis_pedidos.html", {
        "pedidos": pedidos
    })


# ---------------- ADMIN EXTRA ----------------
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

        return redirect("lista_vehiculos")

    return render(request, "dashboard/vehiculo_crear.html")


@login_required
def eliminar_orden(request, id):
    orden = get_object_or_404(Orden, id=id)

    if request.method == "POST":
        orden.delete()

    return redirect("lista_pedidos_admin")


# ---------------- LOGOUT ----------------
def cerrar_sesion(request):
    logout(request)
    return redirect("login")


# ---------------- GESTIÓN DE USUARIOS (FALTABAN ESTAS) ----------------


@login_required
def lista_usuarios(request):
    query = request.GET.get("q")

    usuarios_list = Usuario.objects.all()

    if query:
        usuarios_list = usuarios_list.filter(
            Q(nombre__icontains=query) |
            Q(telefono__icontains=query) |
            Q(rol__icontains=query)
        )

    paginator = Paginator(usuarios_list, 5)
    page = request.GET.get('page')
    usuarios = paginator.get_page(page)

    return render(request, "dashboard/usuarios_lista.html", {
        "usuarios": usuarios,
        "query": query
    })

@login_required
def eliminar_usuario(request, id):
    usuario_obj = get_object_or_404(Usuario, id=id) 
    usuario_obj.delete()
    return redirect("lista_usuarios")

@login_required
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre")
        usuario.telefono = request.POST.get("telefono")
        usuario.rol = request.POST.get("rol")
        usuario.save()
        return redirect("lista_usuarios")
    return render(request, "dashboard/editar_usuario.html", {
        "usuario": usuario
    })

# ---------------- GESTIÓN DE MATERIALES (FALTABAN ESTAS) ----------------

@login_required
def lista_materiales(request):
    materiales = Material.objects.all()
    return render(request, "dashboard/materiales_lista.html", {
        "materiales": materiales
    })

@login_required
def lista_pedidos_admin(request):
    pedidos = Orden.objects.all().order_by("-fecha")
    return render(request, "dashboard/pedidos_lista.html", {
        "pedidos": pedidos
    })
    
    # ---------------- VISTAS ADICIONALES QUE FALTABAN ----------------

@login_required
def lista_conductores(request):
    conductores = Usuario.objects.filter(rol="conductor")
    return render(request, "dashboard/conductores_lista.html", {
        "conductores": conductores
    })

@login_required
def reportes_admin(request):
    total_ordenes = Orden.objects.count()
    context = {
        "total": total_ordenes,
        "pendientes": Orden.objects.filter(estado="pendiente").count(),
        "en_ruta": Orden.objects.filter(estado="en_ruta").count(),
        "entregadas": Orden.objects.filter(estado="entregado").count(),
    }
    return render(request, "dashboard/reportes.html", context)

@login_required
def ver_pedido_admin(request, id):
    pedido = get_object_or_404(Orden, id=id)
    return render(request, "dashboard/pedido_detalle.html", {
        "pedido": pedido
    })

@login_required
def perfil_conductor(request):
    conductor = request.user.usuario
    pedidos = Orden.objects.filter(conductor=conductor)
    return render(request, "usuarios/perfil-conductor.html", {
        "conductor": conductor,
        "pedidos": pedidos
    })

@login_required
def perfil_cliente(request):
    cliente = request.user.usuario
    return render(request, "cliente/perfil.html", {
        "cliente": cliente
    })
    # ---------------- VISTAS DE SEGUIMIENTO E HISTORIAL (FALTANTES) ----------------

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

@login_required
def eliminar_material(request, id):
    material = get_object_or_404(Material, id=id)
    if request.method == "POST":
        material.delete()
        messages.success(request, "Material eliminado correctamente")
    return redirect("lista_materiales")

@login_required
def lista_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    return render(request, "dashboard/vehiculos_lista.html", {
        "vehiculos": vehiculos
    })
    
    # ---------------- GESTIÓN DE MATERIALES (FALTANTES) ----------------

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
        messages.success(request, "Material creado correctamente")
        return redirect("lista_materiales")

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
        messages.success(request, "Material actualizado")
        return redirect("lista_materiales")

    return render(request, "dashboard/material_editar.html", {"material": material})

# ---------------- CONDUCTORES Y REPORTES ----------------

@login_required
def lista_conductores(request):
    conductores = Usuario.objects.filter(rol="conductor")
    return render(request, "dashboard/conductores_lista.html", {"conductores": conductores})

@login_required
def reportes_admin(request):
    context = {
        "total": Orden.objects.count(),
        "pendientes": Orden.objects.filter(estado="pendiente").count(),
        "en_ruta": Orden.objects.filter(estado="en_ruta").count(),
        "entregadas": Orden.objects.filter(estado="entregado").count(),
    }
    return render(request, "dashboard/reportes.html", context)