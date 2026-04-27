from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404

def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            if request.user.usuario.rol == 'admin':
                return view_func(request, *args, **kwargs)
        except Usuario.DoesNotExist:
            if request.user.is_superuser:
                # Si es superusuario pero no tiene perfil, lo creamos como admin
                Usuario.objects.create(
                    user=request.user,
                    rol='admin',
                    nombres=request.user.first_name or "Admin",
                    apellidos=request.user.last_name or "Principal",
                    tipo_documento='CC',
                    documento='12345678'
                )
                return view_func(request, *args, **kwargs)
        raise PermissionDenied
    return _wrapped_view
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Usuario, Administrador, Conductor, Cliente, Material, Vehiculo, Stock, Proveedor
from apps.ordenes.models import Orden

# Proveedores logic moved to apps.compras

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from django.db.models import Sum, Q
from django.utils.timezone import now
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.historial.utils import registrar_actividad
from .forms import LoginForm, RegistroForm, MaterialForm, ProveedorForm

def buscar_usuarios_generales(query=None):
    """
    Lógica unificada para buscar usuarios por nombre, email o documento.
    Optimizado con select_related para evitar N+1 en plantillas.
    """
    usuarios = Usuario.objects.all().select_related('user', 'perfil_cliente').order_by('-id')
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
    Optimizado con select_related para evitar N+1.
    """
    conductores = Usuario.objects.filter(rol="conductor").select_related('user')
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
            try:
                # El formulario ya validó correos, documentos y contraseñas coincidentes
                email = form.cleaned_data.get("correo")
                password = form.cleaned_data.get("contrasena")
                
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password
                )

                # El formulario ModelForm puede guardar el objeto Usuario directamente
                perfil = form.save(commit=False)
                perfil.user = user
                perfil.rol = "cliente"
                perfil.sincronizado = False
                perfil.save()
                
                registrar_actividad(request, 'crear', 'usuarios', user.id, f"Nuevo registro: {email}")
                messages.success(request, "¡Listo! Ya quedó registrado. Ahora puede entrar.")
                return redirect("usuarios:login")
                
            except Exception as e:
                messages.error(request, f"Error al crear el usuario: {str(e)}")
        else:
            # Los errores del formulario se mostrarán en la plantilla
            pass

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
                
                registrar_actividad(request, 'login', 'usuarios', user.id, f"Inicio de sesión: {user.username}")
                
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
                    messages.error(request, "Tu cuenta no tiene un perfil asignado.")
            else:
                messages.error(request, "Usuario o contraseña incorrectos.")
        else:
            # Los errores de validación se manejan en el form
            pass

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
        # Optimizamos consultas usando select_related y prefetch_related si fuera necesario
        context = {
            "pedidos_pendientes": Orden.objects.filter(estado="pendiente").count(),
            "conductores": Usuario.objects.filter(rol="conductor").count(),
            "entregas_hoy": Orden.objects.filter(
                estado="entregado",
                fecha__date=now().date()
            ).count(),
            "clientes": Usuario.objects.filter(rol="cliente").count(),
            "pedidos_recientes": Orden.objects.all().select_related('cliente', 'conductor').order_by("-fecha")[:5]
        }
        return render(request, "usuarios/panel-admin.html", context)
    elif usuario.rol == "cliente":
        return redirect("clientes:panel_cliente")
    elif usuario.rol == "conductor":
        return panel_conductor(request)
    
    return redirect("usuarios:login")


# ---------------- CONDUCTOR ----------------
@login_required
def panel_conductor(request):
    try:
        conductor = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")
        
    pedidos_asignados = Orden.objects.filter(conductor=conductor).select_related('cliente').exclude(estado="entregado")
    entregas_completadas = Orden.objects.filter(conductor=conductor, estado="entregado")
    
    context = {
        "pedidos": pedidos_asignados,
        "entregas_totales": entregas_completadas.count(),
        "pedidos_pendientes": pedidos_asignados.count(),
        "ultima_entrega": entregas_completadas.order_by("-fecha").first()
    }
    return render(request, "usuarios/panel-conductor.html", context)


@login_required
def pedidos_conductor(request):
    conductor = request.user.usuario
    pedidos = Orden.objects.filter(
        conductor=conductor
    ).select_related('cliente').exclude(estado="entregado")
    return render(request, "usuarios/pedidos_conductor.html", {
        "pedidos": pedidos
    })


@login_required
def mis_entregas(request):
    conductor = request.user.usuario
    entregas = Orden.objects.filter(
        conductor=conductor,
        estado="entregado"
    ).select_related('cliente').order_by("-fecha")
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
        "total_ventas": Orden.objects.aggregate(total=Sum("precio"))["total"] or 0,
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
        usuario.sincronizado = False
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
                estado='activo',
                sincronizado=False
            )
            
            # Manejo de la imagen de perfil en la creación
            if 'foto_perfil' in request.FILES:
                perfil.foto_perfil = request.FILES['foto_perfil']
                perfil.save()
            
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
    active_tab = request.GET.get('tab', 'general')
    
    usuarios_list = buscar_usuarios_generales(query)
    
    # Separamos por roles para las pestañas específicas
    admins = usuarios_list.filter(rol='admin')
    clientes = usuarios_list.filter(rol='cliente')
    conductores = usuarios_list.filter(rol='conductor')
    
    context = {
        "usuarios_todos": usuarios_list, # Lista general
        "admins": admins,
        "clientes": clientes,
        "conductores": conductores,
        "query": query,
        "active_tab": active_tab
    }
        
    return render(request, "usuarios/lista.html", context)


@login_required
def toggle_estado_usuario(request, id):
    if request.user.usuario.rol != 'admin':
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("usuarios:panel")

    usuario_obj = get_object_or_404(Usuario, id=id)
    
    # PROTECCIÓN: Nadie puede desactivar al administrador global
    if usuario_obj.user.username == 'Edward_Fonseca':
        messages.error(request, "El Administrador Global no puede ser desactivado.")
        return redirect("usuarios:lista_usuarios")

    nuevo_estado = 'inactivo' if usuario_obj.estado == 'activo' else 'activo'
    usuario_obj.estado = nuevo_estado
    usuario_obj.save()
    
    # También desactivar/activar el usuario de Django
    usuario_obj.user.is_active = (nuevo_estado == 'activo')
    usuario_obj.user.save()

    accion = 'desactivado' if nuevo_estado == 'inactivo' else 'activado'
    registrar_actividad(request, 'editar', 'usuarios', id, f"Usuario {accion}: {usuario_obj.user.username}")
    messages.success(request, f"Usuario {usuario_obj.user.username} {accion} correctamente.")
    return redirect("usuarios:lista_usuarios")


@login_required
def eliminar_usuario(request, id):
    # OBTENER USUARIO A ELIMINAR
    usuario = get_object_or_404(Usuario, id=id)
    
    # VALIDACIÓN: Solo admin puede eliminar
    if request.user.usuario.rol != 'admin':
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect('usuarios:lista_usuarios')
        
    # ACCIÓN: Eliminar (O desactivar según lógica de negocio)
    usuario.delete()
    messages.success(request, f"Usuario {usuario.nombres} eliminado correctamente.")
    return redirect('usuarios:lista_usuarios')


@login_required
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    
    if request.user.usuario.rol != 'admin' and request.user.usuario != usuario:
        messages.error(request, "No tienes permisos para editar este perfil.")
        return redirect("usuarios:panel")

    # PROTECCIÓN: Solo el propio Administrador Global puede editar su perfil
    if usuario.user.username == 'Edward_Fonseca' and request.user.username != 'Edward_Fonseca':
        messages.error(request, "Solo el Administrador Global puede modificar su propia cuenta.")
        return redirect("usuarios:lista_usuarios")

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
                
            usuario.sincronizado = False
            usuario.save()
            registrar_actividad(request, 'editar', 'usuarios', usuario.user.id, f"Perfil de usuario editado: {usuario.user.username}")
            messages.success(request, "Cambios guardados exitosamente.")
            return redirect("usuarios:lista_usuarios")
        except Exception as e:
            messages.error(request, f"Error al guardar los cambios: {str(e)}")
            return render(request, "usuarios/form.html", {
                "usuario": usuario,
                "form_data": request.POST,
                "action": "editar"
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
    def form_valid(self, form):
        # Aseguramos que el correo sea el de edwardf5432@gmail.com configurado en el .env
        return super().form_valid(form)


# ---------------- LOGOUT ----------------
def cerrar_sesion(request):
    if request.user.is_authenticated:
        registrar_actividad(request, 'logout', 'usuarios', request.user.id, f"Cierre de sesión del usuario: {request.user.username}")
    logout(request)
    return redirect("usuarios:login")

# --- NOTIFICACIONES ---
@login_required
def lista_notificaciones(request):
    try:
        notificaciones = request.user.usuario.notificaciones.all().order_by('-fecha')
    except Usuario.DoesNotExist:
        notificaciones = []
    return render(request, "usuarios/notificaciones.html", {"notificaciones": notificaciones})

@login_required
def marcar_notificacion_leida(request, id):
    try:
        notificacion = get_object_or_404(request.user.usuario.notificaciones, id=id)
        notificacion.leida = True
        notificacion.save()
        
        if notificacion.link:
            return redirect(notificacion.link)
    except Usuario.DoesNotExist:
        pass
    return redirect("usuarios:notificaciones")