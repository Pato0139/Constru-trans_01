from django.shortcuts import render, redirect
from .models import *
from ordenes.models import Orden

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Sum
from django.utils.timezone import now


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

        return redirect("login")

    return render(request, "usuarios/registro.html")


def login_usuario(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:

            login(request, user)

            usuario = user.usuario

            if usuario.rol == "admin":
                return redirect("panel")

            elif usuario.rol == "cliente":
                return redirect("panel_cliente")

            elif usuario.rol == "conductor":
                return redirect("panel_conductor")

            elif usuario.rol == "empleado":
                return redirect("panel")

        else:
            return render(request, "usuarios/login.html", {
                "error": "Usuario o contraseña incorrectos"
            })

    return render(request, "usuarios/login.html")


@login_required
def panel(request):

    usuario = request.user.usuario

    if usuario.rol == "admin":

        pedidos_pendientes = Orden.objects.filter(estado="pendiente").count()
        conductores = Usuario.objects.filter(rol="conductor").count()
        entregas_hoy = Orden.objects.filter(
            estado="entregado",
            fecha__date=now().date()
        ).count()
        clientes = Usuario.objects.filter(rol="cliente").count()

        pedidos_recientes = Orden.objects.all().order_by("-fecha")[:5]

        context = {
            "pedidos_pendientes": pedidos_pendientes,
            "conductores": conductores,
            "entregas_hoy": entregas_hoy,
            "clientes": clientes,
            "pedidos_recientes": pedidos_recientes
        }

        return render(request, "dashboard/panel-admin.html", context)

    elif usuario.rol == "cliente":
        return redirect("panel_cliente")

    elif usuario.rol == "conductor":
        return redirect("panel_conductor")

    elif usuario.rol == "empleado":
        return render(request, "usuarios/panel-empleado.html")

    return redirect("login")


@login_required
def panel_conductor(request):

    conductor = request.user.usuario

    pedidos = Orden.objects.filter(conductor=conductor)

    return render(request, "usuarios/panel-conductor.html", {
        "pedidos": pedidos
    })


@login_required
def perfil_conductor(request):

    conductor = request.user.usuario

    vehiculo = None

    pedidos = Orden.objects.filter(conductor=conductor)

    context = {
        "conductor": conductor,
        "vehiculo": vehiculo,
        "pedidos": pedidos
    }

    return render(request, "usuarios/perfil-conductor.html", context)


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


def cerrar_sesion(request):

    logout(request)

    return redirect("login")


@login_required
def lista_usuarios(request):

    usuarios = Usuario.objects.all()

    return render(request, "dashboard/usuarios_lista.html", {
        "usuarios": usuarios
    })


@login_required
def eliminar_usuario(request, id):

    usuario = Usuario.objects.get(id=id)
    usuario.delete()

    return redirect("lista_usuarios")


@login_required
def editar_usuario(request, id):

    usuario = Usuario.objects.get(id=id)

    if request.method == "POST":

        usuario.nombre = request.POST.get("nombre")
        usuario.telefono = request.POST.get("telefono")
        usuario.rol = request.POST.get("rol")

        usuario.save()

        return redirect("lista_usuarios")

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
def lista_vehiculos(request):

    vehiculos = Vehiculo.objects.all()

    return render(request, "dashboard/vehiculos_lista.html", {
        "vehiculos": vehiculos
    })


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

    return render(request, "dashboard/reportes.html", context)


@login_required
def panel_cliente(request):

    cliente = request.user.usuario

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

    return render(request, "cliente/dashboard.html", context)


@login_required
def perfil_cliente(request):

    cliente = request.user.usuario

    return render(request, "cliente/perfil.html", {
        "cliente": cliente
    })


@login_required
def crear_pedido(request):

    cliente = request.user.usuario
    materiales = Material.objects.all()

    if request.method == "POST":

        material_id = request.POST.get("material")
        cantidad = int(request.POST.get("cantidad"))
        direccion = request.POST.get("direccion")

        material = Material.objects.get(id=material_id)

        total = material.precio * cantidad

        Orden.objects.create(
            cliente=cliente,
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


@login_required
def seguimiento_pedidos(request):

    cliente = request.user.usuario

    pedidos = Orden.objects.filter(
        cliente=cliente
    ).order_by("-fecha")

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
def lista_materiales(request):

    materiales = Material.objects.all()

    return render(request, "dashboard/materiales_lista.html", {
        "materiales": materiales
    })


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

    return render(request, "dashboard/material_crear.html")


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

    return render(request, "dashboard/material_editar.html", {
        "material": material
    })


@login_required
def eliminar_material(request, id):

    material = Material.objects.get(id=id)
    material.delete()

    return redirect("lista_materiales")

@login_required
def ver_pedido_admin(request, id):

    pedido = Orden.objects.get(id=id)

    return render(request, "dashboard/pedido_detalle.html", {
        "pedido": pedido
    })
    
@login_required
def lista_pedidos_admin(request):

    pedidos = Orden.objects.all().order_by("-fecha")

    return render(request, "dashboard/pedidos_lista.html", {
        "pedidos": pedidos
    })
    
@login_required
def crear_vehiculo(request):

    if request.method == "POST":

        placa = request.POST.get("placa")
        tipo = request.POST.get("tipo")
        capacidad = request.POST.get("capacidad")

        Vehiculo.objects.create(
            placa=placa,
            tipo=tipo,
            capacidad=capacidad,
            estado="disponible"
        )

        return redirect("lista_vehiculos")

    return render(request, "dashboard/vehiculo_crear.html")