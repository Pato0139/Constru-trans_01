from django.shortcuts import render, redirect
from .models import Usuario, Vehiculo
from Ordenes.models import Orden

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Sum

from .models import Material


# -------------------------
# REGISTRO
# -------------------------
def registro(request):

    if request.method == "POST":

        nombre = request.POST.get("nombre")
        email = request.POST.get("correo")
        telefono = request.POST.get("telefono")
        rol = request.POST.get("rol")

        password = request.POST.get("contrasena")
        confirmar = request.POST.get("confirmar_contrasena")

        if password != confirmar:
            return render(request, "usuarios/registro.html", {
                "error": "Las contraseñas no coinciden"
            })

        # Crear usuario de Django
        user = User.objects.create_user(
            username=email,   # usamos el correo como username
            email=email,
            password=password
        )

        # Crear usuario de tu modelo
        Usuario.objects.create(
            user=user,
            nombre=nombre,
            telefono=telefono,
            rol=rol
        )

        return redirect("login")

    return render(request, "usuarios/registro.html")
# -------------------------
# LOGIN
# -------------------------
def login_usuario(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("panel")

    return render(request, "usuarios/login.html")


# -------------------------
# PANEL SEGÚN ROL
# -------------------------
@login_required
def panel(request):

    usuario = request.user.usuario

    if usuario.rol == "admin":
        return render(request, "Dashboard/panel-admin.html")

    elif usuario.rol == "cliente":
        return redirect("panel_cliente")

    elif usuario.rol == "conductor":
        return render(request, "usuarios/panel-conductor.html")

    elif usuario.rol == "empleado":
        return render(request, "usuarios/panel-sesion.html")


# -------------------------
# LOGOUT
# -------------------------
def cerrar_sesion(request):

    logout(request)

    return redirect("login")


# -------------------------
# LISTA USUARIOS
# -------------------------
@login_required
def lista_usuarios(request):

    usuarios = Usuario.objects.all()

    return render(request, "Dashboard/usuarios_lista.html", {
        "usuarios": usuarios
    })


# -------------------------
# ELIMINAR USUARIO
# -------------------------
@login_required
def eliminar_usuario(request, id):

    usuario = Usuario.objects.get(id=id)
    usuario.delete()

    return redirect("lista_usuarios")


# -------------------------
# EDITAR USUARIO
# -------------------------
@login_required
def editar_usuario(request, id):

    usuario = Usuario.objects.get(id=id)

    if request.method == "POST":

        usuario.nombre = request.POST.get("nombre")
        usuario.telefono = request.POST.get("telefono")
        usuario.rol = request.POST.get("rol")

        usuario.save()

        return redirect("lista_usuarios")

    return render(request, "Dashboard/editar_usuario.html", {
        "usuario": usuario
    })


# -------------------------
# LISTA CONDUCTORES
# -------------------------
@login_required
def lista_conductores(request):

    conductores = Usuario.objects.filter(rol="conductor")

    return render(request, "Dashboard/conductores_lista.html", {
        "conductores": conductores
    })


# -------------------------
# LISTA VEHICULOS
# -------------------------
@login_required
def lista_vehiculos(request):

    vehiculos = Vehiculo.objects.all()

    return render(request, "Dashboard/vehiculos_lista.html", {
        "vehiculos": vehiculos
    })


# -------------------------
# REPORTES ADMIN
# -------------------------
@login_required
def reportes_admin(request):

    total_ordenes = Orden.objects.count()
    pendientes = Orden.objects.filter(estado="pendiente").count()
    en_ruta = Orden.objects.filter(estado="en_ruta").count()
    entregadas = Orden.objects.filter(estado="entregado").count()

    context = {
        "total": total_ordenes,
        "pendientes": pendientes,
        "en_ruta": en_ruta,
        "entregadas": entregadas,
    }

    return render(request, "Dashboard/reportes.html", context)


# -------------------------
# PANEL CLIENTE
# -------------------------
@login_required
def panel_cliente(request):

    cliente = Usuario.objects.get(user=request.user)

    pedidos = Orden.objects.filter(cliente=cliente)

    pedidos_activos = pedidos.filter(estado="pendiente").count()
    entregadas = pedidos.filter(estado="entregado").count()

    total_gastado = pedidos.aggregate(total=Sum("precio"))["total"] or 0

    ultimos_pedidos = pedidos.order_by("-fecha")[:5]

    context = {
        "pedidos_activos": pedidos_activos,
        "entregadas": entregadas,
        "total_gastado": total_gastado,
        "ultimos_pedidos": ultimos_pedidos
    }

    return render(request, "Cliente/dashboard.html", context)

# -------------------------
# LISTA DE MATERIALES
# -------------------------
@login_required
def lista_materiales(request):

    materiales = Material.objects.all()

    return render(request, "Dashboard/materiales_lista.html", {
        "materiales": materiales
    })


# -------------------------
# CREAR MATERIAL
# -------------------------
@login_required
def crear_material(request):

    if request.method == "POST":

        nombre = request.POST.get("nombre")
        descripcion = request.POST.get("descripcion")
        precio = request.POST.get("precio")
        stock = request.POST.get("stock")

        Material.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            precio=precio,
            stock=stock
        )

        return redirect("lista_materiales")

    return render(request, "Dashboard/material_crear.html")


# -------------------------
# EDITAR MATERIAL
# -------------------------
@login_required
def editar_material(request, id):

    material = Material.objects.get(id=id)

    if request.method == "POST":

        material.nombre = request.POST.get("nombre")
        material.descripcion = request.POST.get("descripcion")
        material.precio = request.POST.get("precio")
        material.stock = request.POST.get("stock")

        material.save()

        return redirect("lista_materiales")

    return render(request, "Dashboard/material_editar.html", {
        "material": material
    })


# -------------------------
# ELIMINAR MATERIAL
# -------------------------
@login_required
def eliminar_material(request, id):

    material = Material.objects.get(id=id)
    material.delete()

    return redirect("lista_materiales")
