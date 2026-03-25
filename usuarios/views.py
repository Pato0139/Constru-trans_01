from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from ordenes.models import Orden

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Sum
from django.utils.timezone import now
from django.contrib import messages


<<<<<<< HEAD:Usuarios/views.py
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
=======
# ---------------- REGISTRO ----------------
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py
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

        return redirect("usuarios:login")

    return render(request, "usuarios/registro.html")


<<<<<<< HEAD:Usuarios/views.py
# =========================
# LOGIN
# =========================
=======

>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py
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
<<<<<<< HEAD:Usuarios/views.py
            usuario = user.usuario

            if usuario.rol == "admin":
                return redirect("usuarios:panel")

            elif usuario.rol == "cliente":
                return redirect("usuarios:panel_cliente")

            elif usuario.rol == "conductor":
                return redirect("usuarios:panel_conductor")

            elif usuario.rol == "empleado":
                return redirect("usuarios:panel")
=======

            if hasattr(user, "usuario"):
                rol = user.usuario.rol

                if rol == "admin":
                    return redirect("panel")
                elif rol == "cliente":
                    return redirect("panel_cliente")
                elif rol == "conductor":
                    return redirect("panel_conductor")

            return redirect("panel")
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py

        else:
            return render(request, "usuarios/login.html", {
                "error": "Usuario o contraseña incorrectos"
            })

    return render(request, "usuarios/login.html")

<<<<<<< HEAD:Usuarios/views.py

# =========================
# PANEL ADMIN
# =========================
=======
# ---------------- PANEL ADMIN ----------------
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py
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

<<<<<<< HEAD:Usuarios/views.py
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
=======
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
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py
@login_required
def panel_cliente(request):

    cliente = request.user.usuario
    pedidos = Orden.objects.filter(cliente=cliente)

    context = {
<<<<<<< HEAD:Usuarios/views.py
        "pedidos": pedidos,
=======
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py
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
<<<<<<< HEAD:Usuarios/views.py
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)

    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre")
        usuario.telefono = request.POST.get("telefono")
        usuario.save()
        return redirect("usuarios:lista_usuarios")

    return render(request, "usuarios/editar_usuario.html", {"usuario": usuario})

=======
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
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py

# =========================
# CONDUCTORES / VEHICULOS
# =========================
@login_required
def lista_conductores(request):
    conductores = Usuario.objects.filter(rol="conductor")
    return render(request, "usuarios/conductores.html", {"conductores": conductores})

<<<<<<< HEAD:Usuarios/views.py

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
=======
        Orden.objects.create(
            cliente=cliente,
            material=material,
            cantidad=cantidad,
            direccion_origen="Bodega",
            direccion_destino=direccion,
            precio=total,
            estado="pendiente"
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py
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
<<<<<<< HEAD:Usuarios/views.py
    return render(request, "usuarios/mis_pedidos.html")
=======
    cliente = request.user.usuario

    pedidos = Orden.objects.filter(
        cliente=cliente
    ).order_by("-fecha")

    return render(request, "cliente/mis_pedidos.html", {
        "pedidos": pedidos
    })
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py


# ---------------- ADMIN EXTRA ----------------
@login_required
<<<<<<< HEAD:Usuarios/views.py
def seguimiento_pedidos(request):
    return render(request, "usuarios/seguimiento.html")


@login_required
def historial_pedidos(request):
    return render(request, "usuarios/historial.html")
=======
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
    usuarios = Usuario.objects.all()
    return render(request, "dashboard/usuarios_lista.html", {
        "usuarios": usuarios
    })
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py

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

# =========================
# MATERIALES
# =========================
@login_required
def lista_materiales(request):
    materiales = Material.objects.all()
<<<<<<< HEAD:Usuarios/views.py
    return render(request, "usuarios/materiales.html", {"materiales": materiales})

=======
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
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py

@login_required
def crear_material(request):
    if request.method == "POST":
<<<<<<< HEAD:Usuarios/views.py
        Material.objects.create(
            nombre=request.POST.get("nombre"),
            tipo=request.POST.get("tipo"),
            descripcion=request.POST.get("descripcion"),
            precio=request.POST.get("precio"),
            stock=request.POST.get("stock"),
        )
        return redirect("usuarios:lista_materiales")

    return render(request, "usuarios/crear_material.html")

=======
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
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py

@login_required
def editar_material(request, id):
    material = get_object_or_404(Material, id=id)
    if request.method == "POST":
        material.nombre = request.POST.get("nombre")
<<<<<<< HEAD:Usuarios/views.py
        material.precio = request.POST.get("precio")
        material.stock = request.POST.get("stock")
        material.save()
        return redirect("usuarios:lista_materiales")

    return render(request, "usuarios/editar_material.html", {"material": material})
=======
        material.descripcion = request.POST.get("descripcion")
        material.tipo = request.POST.get("tipo")
        material.precio = request.POST.get("precio")
        material.stock = request.POST.get("stock")
        material.save()
        messages.success(request, "Material actualizado")
        return redirect("lista_materiales")

    return render(request, "dashboard/material_editar.html", {"material": material})
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py

# ---------------- CONDUCTORES Y REPORTES ----------------

@login_required
<<<<<<< HEAD:Usuarios/views.py
def eliminar_material(request, id):
    material = get_object_or_404(Material, id=id)
    material.delete()
    return redirect("usuarios:lista_materiales")

=======
def lista_conductores(request):
    conductores = Usuario.objects.filter(rol="conductor")
    return render(request, "dashboard/conductores_lista.html", {"conductores": conductores})
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py

# =========================
# PERFILES
# =========================
@login_required
<<<<<<< HEAD:Usuarios/views.py
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
=======
def reportes_admin(request):
    context = {
        "total": Orden.objects.count(),
        "pendientes": Orden.objects.filter(estado="pendiente").count(),
        "en_ruta": Orden.objects.filter(estado="en_ruta").count(),
        "entregadas": Orden.objects.filter(estado="entregado").count(),
    }
    return render(request, "dashboard/reportes.html", context)
>>>>>>> 248401ded1cafc672837167d1905cb8dd0e13caa:usuarios/views.py
