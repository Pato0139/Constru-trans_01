from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from ordenes.models import Orden

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Sum
from django.utils.timezone import now


# =========================
# LISTA DE USUARIOS (ADMIN)
# =========================
@login_required
def lista_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, "usuarios/lista_usuarios.html", {"usuarios": usuarios})


# =========================
# REGISTRO
# =========================
def registro(request):

    if request.method == "POST":

        nombre = request.POST.get("nombre")
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

        return redirect("usuarios:login")

    return render(request, "usuarios/registro.html")


# =========================
# LOGIN
# =========================
def login_usuario(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:

            login(request, user)
            usuario = user.usuario

            if usuario.rol == "admin":
                return redirect("usuarios:panel")

            elif usuario.rol == "cliente":
                return redirect("usuarios:panel_cliente")

            elif usuario.rol == "conductor":
                return redirect("usuarios:panel_conductor")

            elif usuario.rol == "empleado":
                return redirect("usuarios:panel")

        else:
            return render(request, "usuarios/login.html", {
                "error": "Usuario o contraseña incorrectos"
            })

    return render(request, "usuarios/login.html")


# =========================
# PANEL ADMIN
# =========================
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

    elif usuario.rol == "cliente":
        return redirect("usuarios:panel_cliente")

    elif usuario.rol == "conductor":
        return redirect("usuarios:panel_conductor")

    elif usuario.rol == "empleado":
        return render(request, "usuarios/panel-empleado.html")

    return redirect("usuarios:login")


# =========================
# PANEL CONDUCTOR
# =========================
@login_required
def panel_conductor(request):
    pedidos = Orden.objects.filter(conductor=request.user.usuario)
    return render(request, "usuarios/panel-conductor.html", {"pedidos": pedidos})


# =========================
# PANEL CLIENTE
# =========================
@login_required
def panel_cliente(request):

    cliente = request.user.usuario
    pedidos = Orden.objects.filter(cliente=cliente)

    context = {
        "pedidos": pedidos,
        "pedidos_activos": pedidos.filter(estado="pendiente").count(),
        "entregadas": pedidos.filter(estado="entregado").count(),
        "total_gastado": pedidos.aggregate(total=Sum("precio"))["total"] or 0,
        "ultimos_pedidos": pedidos.order_by("-fecha")[:5]
    }

    return render(request, "usuarios/panel-clientes.html", context)



# =========================
# CERRAR SESIÓN
# =========================
def cerrar_sesion(request):
    logout(request)
    return redirect("usuarios:login")


# =========================
# USUARIOS CRUD
# =========================
@login_required
def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    usuario.delete()
    return redirect("usuarios:lista_usuarios")


@login_required
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)

    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre")
        usuario.telefono = request.POST.get("telefono")
        usuario.save()
        return redirect("usuarios:lista_usuarios")

    return render(request, "usuarios/editar_usuario.html", {"usuario": usuario})


# =========================
# CONDUCTORES / VEHICULOS
# =========================
@login_required
def lista_conductores(request):
    conductores = Usuario.objects.filter(rol="conductor")
    return render(request, "usuarios/conductores.html", {"conductores": conductores})


@login_required
def lista_vehiculos(request):
    vehiculos = Vehiculo.objects.all()
    return render(request, "usuarios/vehiculos.html", {"vehiculos": vehiculos})


@login_required
def crear_vehiculo(request):

    if request.method == "POST":
        Vehiculo.objects.create(
            placa=request.POST.get("placa"),
            tipo=request.POST.get("tipo"),
            capacidad=request.POST.get("capacidad"),
            estado=request.POST.get("estado"),
        )
        return redirect("usuarios:lista_vehiculos")

    return render(request, "usuarios/crear_vehiculo.html")


# =========================
# PEDIDOS
# =========================
@login_required
def lista_pedidos_admin(request):
    pedidos = Orden.objects.all()
    return render(request, "usuarios/pedidos_admin.html", {"pedidos": pedidos})


@login_required
def ver_pedido_admin(request, id):
    pedido = get_object_or_404(Orden, id=id)
    return render(request, "usuarios/ver_pedido.html", {"pedido": pedido})


@login_required
def pedidos_conductor(request):
    pedidos = Orden.objects.filter(conductor=request.user.usuario)
    return render(request, "usuarios/pedidos_conductor.html", {"pedidos": pedidos})


@login_required
def mis_entregas(request):
    entregas = Orden.objects.filter(
        conductor=request.user.usuario,
        estado="entregado"
    )
    return render(request, "usuarios/mis_entregas.html", {"entregas": entregas})


# =========================
# CLIENTE PEDIDOS
# =========================
@login_required
def crear_pedido(request):
    return render(request, "usuarios/crear_pedido.html")


@login_required
def mis_pedidos(request):
    return render(request, "usuarios/mis_pedidos.html")


@login_required
def seguimiento_pedidos(request):
    return render(request, "usuarios/seguimiento.html")


@login_required
def historial_pedidos(request):
    return render(request, "usuarios/historial.html")


# =========================
# MATERIALES
# =========================
@login_required
def lista_materiales(request):
    materiales = Material.objects.all()
    return render(request, "usuarios/materiales.html", {"materiales": materiales})


@login_required
def crear_material(request):

    if request.method == "POST":
        Material.objects.create(
            nombre=request.POST.get("nombre"),
            tipo=request.POST.get("tipo"),
            descripcion=request.POST.get("descripcion"),
            precio=request.POST.get("precio"),
            stock=request.POST.get("stock"),
        )
        return redirect("usuarios:lista_materiales")

    return render(request, "usuarios/crear_material.html")


@login_required
def editar_material(request, id):
    material = get_object_or_404(Material, id=id)

    if request.method == "POST":
        material.nombre = request.POST.get("nombre")
        material.precio = request.POST.get("precio")
        material.stock = request.POST.get("stock")
        material.save()
        return redirect("usuarios:lista_materiales")

    return render(request, "usuarios/editar_material.html", {"material": material})


@login_required
def eliminar_material(request, id):
    material = get_object_or_404(Material, id=id)
    material.delete()
    return redirect("usuarios:lista_materiales")


# =========================
# PERFILES
# =========================
@login_required
def perfil_cliente(request):
    return render(request, "usuarios/perfil_cliente.html", {
        "usuario": request.user.usuario
    })


@login_required
def perfil_conductor(request):
    return render(request, "usuarios/perfil_conductor.html", {
        "usuario": request.user.usuario
    })


# =========================
# REPORTES
# =========================
@login_required
def reportes_admin(request):

    context = {
        "total_pedidos": Orden.objects.count(),
        "total_clientes": Usuario.objects.filter(rol="cliente").count()
    }

    return render(request, "usuarios/reportes.html", context)