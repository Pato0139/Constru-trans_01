from django.shortcuts import render, redirect, get_object_or_404
from .models import *
from apps.ordenes.models import Orden

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Sum, Q
from django.utils.timezone import now
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from historial.utils import registrar_actividad
from .forms import LoginForm, RegistroForm

def buscar_usuarios_generales(query=None):
    """
    Lógica unificada para buscar usuarios por nombre, email o documento.
    """
    usuarios = Usuario.objects.all().order_by('-id')
    if query:
        usuarios = usuarios.filter(
            Q(nombres__icontains=query) | 
            Q(user__email__icontains=query) |
            Q(documento__icontains=query)
        )
    return usuarios

def buscar_conductores(query=None):
    """
    Lógica unificada para buscar conductores por múltiples campos.
    """
    conductores = Usuario.objects.filter(rol="conductor")
    if query:
        conductores = conductores.filter(
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(user__email__icontains=query) |
            Q(documento__icontains=query) |
            Q(telefono__icontains=query)
        )
    return conductores


# ---------------- REGISTRO ----------------
def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("correo")
            username = email  # Usar el correo como nombre de usuario por simplicidad
            
            nombres = form.cleaned_data.get("nombres")
            apellidos = form.cleaned_data.get("apellidos")
            telefono = form.cleaned_data.get("telefono")
            tipo_documento = form.cleaned_data.get("tipo_documento")
            documento = form.cleaned_data.get("documento")
            rol = "cliente" # Rol predeterminado (HU-01)
            password = form.cleaned_data.get("contrasena")
            confirm_password = form.cleaned_data.get("confirmar_contrasena")

            if password != confirm_password:
                return render(request, "usuarios/registro.html", {
                    "error": "Las contraseñas no coinciden",
                    "form": form
                })

            if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
                return render(request, "usuarios/registro.html", {
                    "error": "Este correo ya está registrado",
                    "form": form
                })

            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password
                )

                Usuario.objects.create(
                    user=user,
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                    rol=rol,
                    tipo_documento=tipo_documento,
                    documento=documento
                )
                
                registrar_actividad(request, 'crear', 'usuarios', user.id, f"Nuevo registro de usuario: {email} como {rol}")
                
                messages.success(request, "Registro exitoso. Ahora puedes iniciar sesión.")
                return redirect("usuarios:login")
                
            except Exception as e:
                return render(request, "usuarios/registro.html", {
                    "error": f"Error al crear el usuario: {str(e)}",
                    "form": form
                })
        else:
            return render(request, "usuarios/registro.html", {
                "error": "Por favor revisa los datos ingresados y marca la casilla 'No soy un robot'.",
                "form": form
            })

    else:
        form = RegistroForm()

    return render(request, "usuarios/registro.html", {"form": form})


from django.contrib.auth import views as auth_views

from .forms import LoginForm


# ---------------- LOGIN ----------------
def login_usuario(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user = authenticate(request, username=identifier, password=password)

            if user is None:
                try:
                    user_obj = User.objects.get(email=identifier)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None

            if user is not None:
                login(request, user)
                
                registrar_actividad(request, 'login', 'usuarios', user.id, f"Inicio de sesión del usuario: {user.username}")
                
                if user.is_superuser:
                    Usuario.objects.get_or_create(
                        user=user,
                        defaults={
                            'nombres': user.username, 
                            'apellidos': 'Admin', 
                            'rol': 'admin',
                            'tipo_documento': 'CC',
                            'documento': '00000000'
                        }
                    )
                    return redirect(request.GET.get('next') or "usuarios:panel")

                perfil = Usuario.objects.filter(user=user).first()
                if perfil:
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    
                    if perfil.rol == "admin":
                        return redirect("usuarios:panel")
                    elif perfil.rol == "cliente":
                        return redirect("clientes:panel_cliente")
                    elif perfil.rol == "conductor":
                        return redirect("usuarios:panel_conductor")
                    else:
                        return redirect("usuarios:panel")
                else:
                    logout(request)
                    return render(request, "usuarios/login.html", {
                        "error": "Tu cuenta no tiene un perfil asignado.",
                        "form": form
                    })
            else:
                return render(request, "usuarios/login.html", {
                    "error": "Usuario o contraseña incorrectos",
                    "form": form
                })
        else:
            return render(request, "usuarios/login.html", {
                "error": "Por favor marca la casilla 'No soy un robot'.",
                "form": form
            })

    else:
        form = LoginForm()

    return render(request, "usuarios/login.html", {"form": form})


# ---------------- PANEL ADMIN ----------------
@login_required
def panel(request):
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        if request.user.is_superuser:
            usuario = Usuario.objects.create(
                user=request.user,
                nombres=request.user.username,
                apellidos='Admin',
                rol='admin',
                tipo_documento='CC',
                documento='00000000',
                estado='activo'
            )
        else:
            logout(request)
            return redirect("usuarios:login")

    if usuario.rol == "admin":
        try:
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
        except Exception as e:
            registrar_actividad(request, 'error', 'panel', None, f"Error al cargar estadísticas: {str(e)}")
            context = {
                "pedidos_pendientes": 0,
                "conductores": 0,
                "entregas_hoy": 0,
                "clientes": 0,
                "pedidos_recientes": []
            }
        return render(request, "usuarios/panel-admin.html", context)
    elif usuario.rol == "cliente":
        return redirect("clientes:panel_cliente")
    elif usuario.rol == "conductor":
        return panel_conductor(request)
    
    return redirect("usuarios:login")


# ---------------- STOCK ----------------
@login_required
def stock_lista(request):
    """
    Vista para el panel de control de stock de materiales.
    """
    if request.user.usuario.rol != 'admin':
        messages.error(request, "No tienes permisos para ver el inventario.")
        return redirect("usuarios:panel")

    q = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    alerta = request.GET.get('alerta', '')

    stocks = StockMaterial.objects.all().select_related('material')

    if q:
        stocks = stocks.filter(
            Q(material__nombre__icontains=q) |
            Q(material__tipo__icontains=q)
        )
    
    if tipo:
        stocks = stocks.filter(material__tipo=tipo)

    # Alerta de stock bajo (cantidad_actual <= cantidad_minima)
    if alerta == 'bajo':
        stocks = [s for s in stocks if s.cantidad_actual <= s.cantidad_minima]

    # Paginación (6 por página para diseño de tarjetas)
    paginator = Paginator(stocks, 6)
    page = request.GET.get('page')
    try:
        stocks_paginados = paginator.page(page)
    except PageNotAnInteger:
        stocks_paginados = paginator.page(1)
    except EmptyPage:
        stocks_paginados = paginator.page(paginator.num_pages)

    tipos_materiales = Material.objects.values_list('tipo', flat=True).distinct()

    return render(request, "inventario/stock_dashboard.html", {
        "stocks": stocks_paginados,
        "query": q,
        "tipo_selected": tipo,
        "alerta": alerta,
        "tipos_materiales": tipos_materiales
    })


# ---------------- CONDUCTOR ----------------
@login_required
def panel_conductor(request):
    try:
        conductor = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")
        
    pedidos_asignados = Orden.objects.filter(conductor=conductor).exclude(estado="entregado")
    entregas_completadas = Orden.objects.filter(conductor=conductor, estado="entregado")
    
    # Obtener vehículo asignado (basado en la lógica del perfil)
    # Asumiendo que hay una relación o filtro por placa/estado si no hay FK directa en Usuario
    vehiculo = Vehiculo.objects.filter(estado="en_ruta").first() # Simplificación para demo si no hay FK
    
    # Rendimiento: Promedio de entregas por semana (simulado o calculado)
    # Por ahora usaremos datos reales de las órdenes
    context = {
        "pedidos": pedidos_asignados[:5], # Solo los 5 más recientes
        "entregas_totales": entregas_completadas.count(),
        "pedidos_pendientes": pedidos_asignados.count(),
        "ultima_entrega": entregas_completadas.order_by("-fecha").first(),
        "vehiculo": vehiculo,
        "notificaciones": [
            {"titulo": "Nueva Ruta Asignada", "tipo": "info", "fecha": "Hace 5 min"},
            {"titulo": "Mantenimiento Preventivo", "tipo": "warning", "fecha": "Mañana 8:00 AM"}
        ]
    }
    return render(request, "usuarios/panel-conductor.html", context)


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


@login_required
def perfil_admin(request):
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")
        
    context = {
        "usuario": usuario,
        "usuarios_count": Usuario.objects.count(),
        "materiales_count": Material.objects.count(),
        "ordenes_count": Orden.objects.count(),
        "total_ventas": Orden.objects.aggregate(total=Sum("total_pagar"))["total"] or 0,
        "entregados_count": Orden.objects.filter(estado="entregado").count()
    }
    return render(request, "usuarios/detalle.html", context)


@login_required
def editar_perfil(request):
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")
        
    if request.method == "POST":
        nombres = request.POST.get("nombres")
        apellidos = request.POST.get("apellidos")
        telefono = request.POST.get("telefono")
        tipo_documento = request.POST.get("tipo_documento")
        documento = request.POST.get("documento")
        email = request.POST.get("email")
        
        # Manejo de la imagen de perfil
        if 'foto_perfil' in request.FILES:
            usuario.foto_perfil = request.FILES['foto_perfil']
            
        usuario.nombres = nombres
        usuario.apellidos = apellidos
        usuario.telefono = telefono
        usuario.tipo_documento = tipo_documento
        usuario.documento = documento
        usuario.save()
        
        # Actualizar el correo del User de Django
        if email:
            request.user.email = email
            request.user.save()
            
        messages.success(request, "Perfil actualizado correctamente.")
        
        if usuario.rol == 'admin':
            return redirect("usuarios:perfil_admin")
        elif usuario.rol == 'conductor':
            return redirect("usuarios:perfil_conductor")
        else:
            return redirect("clientes:perfil_cliente")
            
    return render(request, "usuarios/editar_perfil.html", {"usuario": usuario})


@login_required
def perfil(request):
    """
    Vista genérica de perfil que redirige según el rol del usuario.
    """
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")

    if usuario.rol == 'admin':
        return redirect("usuarios:perfil_admin")
    elif usuario.rol == 'conductor':
        return redirect("usuarios:perfil_conductor")
    else:
        return redirect("clientes:panel_cliente")


@login_required
def perfil(request):
    """
    Vista genérica de perfil que redirige según el rol del usuario.
    """
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        if request.user.is_superuser:
            return redirect("usuarios:perfil_admin")
        logout(request)
        return redirect("usuarios:login")

    if usuario.rol == 'admin':
        return redirect("usuarios:perfil_admin")
    elif usuario.rol == 'conductor':
        return redirect("usuarios:perfil_conductor")
    elif usuario.rol == 'cliente':
        return redirect("clientes:perfil_cliente")
    else:
        return redirect("usuarios:panel")


# ---------------- GESTIÓN DE USUARIOS ----------------
@login_required
def crear_usuario(request):
    if request.user.usuario.rol != 'admin':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "error", "message": "No tienes permisos."}, status=403)
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("usuarios:panel")

    if request.method == "POST":
        nombres = request.POST.get("nombres")
        apellidos = request.POST.get("apellidos")
        email = request.POST.get("email")
        password = request.POST.get("password")
        telefono = request.POST.get("telefono")
        rol = request.POST.get("rol")
        tipo_doc = request.POST.get("tipo_doc")
        documento = request.POST.get("documento")

        if not all([nombres, apellidos, email, password, telefono, rol, tipo_doc, documento]):
            error_msg = "Todos los campos son obligatorios."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            return render(request, "usuarios/form.html", {"form_data": request.POST, "action": "crear"})

        if User.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
            error_msg = "Este correo electrónico ya está registrado."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            return render(request, "usuarios/form.html", {"form_data": request.POST, "action": "crear"})

        try:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password
            )

            perfil = Usuario.objects.create(
                user=user,
                nombres=nombres,
                apellidos=apellidos,
                telefono=telefono,
                rol=rol,
                tipo_documento=tipo_doc,
                documento=documento,
                estado='activo'
            )
            
            registrar_actividad(request, 'crear', 'usuarios', user.id, f"Administrador creó usuario: {email} como {rol}")

            success_msg = f"Usuario {nombres} creado correctamente."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"status": "success", "message": success_msg})
            
            messages.success(request, success_msg)
            return redirect("usuarios:lista_usuarios")
        except Exception as e:
            error_msg = f"Error al crear usuario: {str(e)}"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"status": "error", "message": error_msg}, status=500)
            
            messages.error(request, error_msg)
            return render(request, "usuarios/form.html", {
                "error": error_msg,
                "form_data": request.POST,
                "action": "crear"
            })

    return render(request, "usuarios/form.html", {"action": "crear", "form_data": {}})

@login_required
def lista_usuarios(request):
    query = request.GET.get('q')
    usuarios_list = buscar_usuarios_generales(query)
    
    admins_list = usuarios_list.filter(rol='admin')
    clientes_list = usuarios_list.filter(rol='cliente')
    conductores_list = usuarios_list.filter(rol='conductor')
    
    # Paginación para cada tipo
    page_admin = request.GET.get('page_admin')
    page_cliente = request.GET.get('page_cliente')
    page_conductor = request.GET.get('page_conductor')

    paginator_admin = Paginator(admins_list, 10)
    paginator_cliente = Paginator(clientes_list, 10)
    paginator_conductor = Paginator(conductores_list, 10)

    try:
        admins = paginator_admin.page(page_admin)
    except:
        admins = paginator_admin.page(1)

    try:
        clientes = paginator_cliente.page(page_cliente)
    except:
        clientes = paginator_cliente.page(1)

    try:
        conductores = paginator_conductor.page(page_conductor)
    except:
        conductores = paginator_conductor.page(1)
    
    context = {
        "admins": admins,
        "clientes": clientes,
        "conductores": conductores,
        "query": query
    }
        
    return render(request, "usuarios/lista.html", context)


@login_required
def eliminar_usuario(request, id):
    if request.user.usuario.rol != 'admin':
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("usuarios:panel")

    usuario_obj = get_object_or_404(Usuario, id=id)
    
    # Restricción: Un admin no puede eliminar a otro admin (a menos que sea superuser)
    if usuario_obj.rol == 'admin' and usuario_obj.user != request.user and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para eliminar a otro administrador.")
        return redirect("usuarios:lista_usuarios")

    nombre_usuario = usuario_obj.user.username
    usuario_obj.delete()
    registrar_actividad(request, 'eliminar', 'usuarios', id, f"Usuario eliminado: {nombre_usuario}")
    messages.success(request, "Usuario eliminado correctamente.")
    return redirect("usuarios:lista_usuarios")


@login_required
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    
    # Restricción: Un admin no puede editar a otro admin (a menos que sea superuser o sea él mismo)
    if usuario.rol == 'admin' and usuario.user != request.user and not request.user.is_superuser:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"status": "error", "message": "No tienes permisos para editar a otro administrador."}, status=403)
        messages.error(request, "No tienes permisos para editar a otro administrador.")
        return redirect("usuarios:lista_usuarios")
    
    if request.user.usuario.rol != 'admin' and request.user.usuario != usuario:
        messages.error(request, "No tienes permisos para editar este perfil.")
        return redirect("usuarios:panel")

    if request.method == "POST":
        nombres = request.POST.get("nombres")
        apellidos = request.POST.get("apellidos")
        telefono = request.POST.get("telefono")
        rol = request.POST.get("rol")

        if not all([nombres, apellidos, telefono]):
            messages.error(request, "Los campos nombres, apellidos y teléfono son obligatorios.")
            return render(request, "usuarios/form.html", {
                "usuario": usuario,
                "form_data": request.POST,
                "action": "editar"
            })

        try:
            usuario.nombres = nombres
            usuario.apellidos = apellidos
            usuario.telefono = telefono
            
            # Manejo de la imagen de perfil en la edición de usuario por admin
            if 'foto_perfil' in request.FILES:
                usuario.foto_perfil = request.FILES['foto_perfil']
                
            if request.user.usuario.rol == "admin" and rol:
                usuario.rol = rol
                
            usuario.save()
            registrar_actividad(request, 'editar', 'usuarios', usuario.user.id, f"Perfil de usuario editado: {usuario.user.username}")
            
            success_msg = "Cambios guardados exitosamente."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"status": "success", "message": success_msg})
                
            messages.success(request, success_msg)
            return redirect("usuarios:lista_usuarios")
        except Exception as e:
            error_msg = f"Error al guardar los cambios: {str(e)}"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"status": "error", "message": error_msg}, status=500)
                
            messages.error(request, error_msg)
            return render(request, "usuarios/form.html", {
                "usuario": usuario,
                "form_data": request.POST,
                "action": "editar"
            })

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            "id": usuario.id,
            "nombres": usuario.nombres,
            "apellidos": usuario.apellidos,
            "email": usuario.user.email,
            "telefono": usuario.telefono,
            "rol": usuario.rol,
            "tipo_doc": usuario.tipo_documento,
            "documento": usuario.documento
        })

    return render(request, "usuarios/form.html", {
        "usuario": usuario,
        "form_data": {},
        "action": "editar"
    })


@login_required
def lista_conductores(request):
    conductores = Usuario.objects.filter(rol="conductor")
    return render(request, "usuarios/conductores_lista.html", {
        "conductores": conductores
    })


@login_required
def perfil_conductor(request):
    conductor_id = request.GET.get('id')
    
    if conductor_id and request.user.usuario.rol == 'admin':
        conductor = get_object_or_404(Usuario, id=conductor_id)
    else:
        try:
            conductor = request.user.usuario
        except Usuario.DoesNotExist:
            logout(request)
            return redirect("usuarios:login")
        
    pedidos = Orden.objects.filter(conductor=conductor)
    
    from apps.ordenes.models import Entrega
    ultima_entrega = Entrega.objects.filter(conductor=conductor).order_by('-fecha').first()
    vehiculo = ultima_entrega.vehiculo if ultima_entrega else None

    return render(request, "usuarios/perfil-conductor.html", {
        "conductor": conductor,
        "pedidos": pedidos,
        "vehiculo": vehiculo
    })


# ---------------- PASSWORD RESET ----------------
class CustomPasswordResetView(auth_views.PasswordResetView):
    pass


# ---------------- LOGOUT ----------------
def cerrar_sesion(request):
    if request.user.is_authenticated:
        registrar_actividad(request, 'logout', 'usuarios', request.user.id, f"Cierre de sesión del usuario: {request.user.username}")
    logout(request)
    return redirect("usuarios:login")
