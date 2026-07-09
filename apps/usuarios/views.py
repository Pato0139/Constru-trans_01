import logging
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

User = get_user_model()
from django.contrib.auth.views import PasswordResetView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Prefetch, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.timezone import now

from apps.historial.utils import registrar_actividad
from apps.ordenes.models import Pedido
from core.db_preference import PREF_LOCAL, PREF_REMOTA, invalidate_connection_cache
from core.sync import sync_all_usuarios
from core.utils import conexion_remota_disponible

from .forms import AsignarVehiculoForm, LoginForm, RegistroForm
from .models import (
    Conductor,
    ConductorVehiculo,
    Usuario,
)
from .models import (
    MaterialConstruccion as Material,
)
from .utils import limpiar_telefono

logger = logging.getLogger(__name__)


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            if request.user.usuario.rol == "admin":
                return view_func(request, *args, **kwargs)
        except Usuario.DoesNotExist:
            if request.user.is_superuser:
                Usuario.objects.create(
                    user=request.user,
                    rol="admin",
                    nombres=request.user.first_name or "Admin",
                    apellidos=request.user.last_name or "Principal",
                    tipo_documento="CC",
                    documento="12345678",
                )
                return view_func(request, *args, **kwargs)
        raise PermissionDenied

    return _wrapped_view


def buscar_usuarios_generales(query=None):
    """
    Lógica unificada para buscar usuarios por nombre, email o documento.
    Optimizado con select_related para evitar N+1 en plantillas.
    """
    usuarios = Usuario.objects.all().select_related("perfil_cliente").order_by("-id")
    if query:
        usuarios = usuarios.filter(
            Q(nombres__icontains=query) | Q(email__icontains=query) | Q(documento__icontains=query)
        )
    return usuarios


def buscar_conductores(query=None):
    """
    Lógica unificada para buscar conductores por múltiples campos.
    Optimizado con select_related para evitar N+1.
    """
    conductores = Usuario.objects.filter(rol="conductor")
    if query:
        conductores = conductores.filter(
            Q(nombres__icontains=query)
            | Q(apellidos__icontains=query)
            | Q(email__icontains=query)
            | Q(documento__icontains=query)
            | Q(telefono__icontains=query)
        )
    return conductores


# =====================================================================
# REGISTRO
# =====================================================================


def registro(request):
    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            try:
                email = form.cleaned_data.get("correo")
                password = form.cleaned_data.get("contrasena")

                with transaction.atomic():
                    try:
                        user = form.save(commit=False)
                        user.username = email
                        user.email = email
                        user.set_password(password)
                        user.rol = "cliente"
                        user.sincronizado = False
                        user.estado = "activo"
                        user.save()
                    except Exception as e:
                        if "duplicate key" in str(e).lower() and conexion_remota_disponible():
                            from django.db import connections

                            try:
                                with connections["remota"].cursor() as cursor:
                                    cursor.execute(
                                        "SELECT setval(pg_get_serial_sequence('usuario', 'id'), (SELECT MAX(id) FROM usuario));"
                                    )
                            except Exception:
                                pass

                            user = form.save(commit=False)
                            user.username = email
                            user.email = email
                            user.set_password(password)
                            user.rol = "cliente"
                            user.sincronizado = False
                            user.estado = "activo"
                            user.save()
                        else:
                            raise e

                    registrar_actividad(
                        request, "crear", "usuarios", user.id, f"Nuevo registro: {email}"
                    )

                messages.success(request, "¡Listo! Ya quedó registrado. Ahora puede entrar.")
                return redirect("usuarios:login")

            except Exception as e_final:
                messages.error(request, f"Error al crear el usuario: {str(e_final)}")
        else:
            pass

    else:
        form = RegistroForm()

    context = {"form": form}

    return render(request, "usuarios/registro.html", context)


# =====================================================================
# LOGIN
# =====================================================================


def login_usuario(request):
    if conexion_remota_disponible():
        try:
            sync_all_usuarios()
        except Exception as e:
            logger.error(f"Error sincronizando en login: {e}")

    modo_local = not conexion_remota_disponible()

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
                if user.rol == "cliente":
                    from apps.clientes.models import Cliente

                    try:
                        Cliente.objects.get_or_create(usuario=user)
                    except Exception as e_c:
                        if "duplicate key" in str(e_c).lower() and conexion_remota_disponible():
                            from django.db import connections

                            try:
                                with connections["remota"].cursor() as cursor:
                                    cursor.execute(
                                        "SELECT setval(pg_get_serial_sequence('perfil_cliente', 'id'), (SELECT MAX(id) FROM perfil_cliente));"
                                    )
                            except Exception:
                                pass
                            Cliente.objects.get_or_create(usuario=user)
                        else:
                            raise e_c

                if not hasattr(user, "backend"):
                    user.backend = "django.contrib.auth.backends.ModelBackend"

                login(request, user)

                remember_me = form.cleaned_data.get("remember_me")
                if remember_me:
                    request.session.set_expiry(1209600)
                else:
                    request.session.set_expiry(0)

                request.session.save()

                try:
                    registrar_actividad(
                        request, "login", "usuarios", user.id, f"Inicio de sesión: {user.username}"
                    )
                except Exception:
                    pass

                messages.success(request, f"¡Bienvenido de nuevo, {user.nombres}!")

                from django.utils.http import url_has_allowed_host_and_scheme

                next_url = request.GET.get("next")
                if next_url and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)

                if user.rol == "admin":
                    return redirect("usuarios:panel")
                elif user.rol == "cliente":
                    return redirect("clientes:panel_cliente")
                elif user.rol == "conductor":
                    return redirect("usuarios:panel_conductor")
                else:
                    return redirect("usuarios:panel")
            else:
                messages.error(request, "Usuario o contraseña incorrectos.")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            pass

    else:
        form = LoginForm()

    context = {"form": form, "modo_local": modo_local}

    return render(request, "usuarios/login.html", context)


# =====================================================================
# PANEL ADMIND
# =====================================================================


@login_required
def panel(request):
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        usuario = Usuario.objects.create(
            user=request.user,
            nombres=request.user.username.split("@")[0],
            apellidos="Admin" if request.user.is_staff else "Usuario",
            rol="admin" if request.user.is_staff else "cliente",
            tipo_documento="CC",
            documento="00000000",
            estado="activo",
        )
        if usuario.rol == "cliente":
            from apps.clientes.models import Cliente

            try:
                Cliente.objects.get_or_create(usuario=usuario)
            except Exception as e_c:
                if "duplicate key" in str(e_c).lower() and conexion_remota_disponible():
                    from django.db import connections

                    with connections["remota"].cursor() as cursor:
                        cursor.execute(
                            "SELECT setval(pg_get_serial_sequence('perfil_cliente', 'id'), (SELECT MAX(id) FROM perfil_cliente));"
                        )
                    Cliente.objects.get_or_create(usuario=usuario)
                else:
                    raise e_c

    if usuario.rol == "admin":
        from django.core.cache import cache

        from core.utils import get_cache_key

        cache_key = get_cache_key("panel_admin_v2", request.user.id)

        context = cache.get(cache_key)

        if not context:
            context = {
                "pedidos_pendientes": Pedido.objects.filter(estado="pendiente").count(),
                "conductores": Usuario.objects.filter(rol="conductor").count(),
                "entregas_hoy": Pedido.objects.filter(
                    estado="entregado", fecha_solicitud__date=now().date()
                ).count(),
                "clientes": Usuario.objects.filter(rol="cliente").count(),
                "pedidos_recientes": Pedido.objects.select_related(
                    "usuario", "cliente__usuario"
                ).order_by("-fecha_solicitud")[:5],
            }
            cache.set(cache_key, context, 300)

        return render(request, "usuarios/panel-admin.html", context)
    elif usuario.rol == "cliente":
        return redirect("clientes:panel_cliente")
    elif usuario.rol == "conductor":
        return panel_conductor(request)

    return redirect("usuarios:login")


# =====================================================================
# CONDUCTOR
# =====================================================================


@login_required
def panel_conductor(request):
    try:
        conductor = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")

    pedidos_asignados = (
        Pedido.objects.filter(conductor=conductor)
        .select_related("usuario", "cliente__usuario")
        .exclude(estado="entregado")
    )
    entregas_completadas = Pedido.objects.filter(conductor=conductor, estado="entregado")

    context = {
        "pedidos": pedidos_asignados,
        "entregas_totales": entregas_completadas.count(),
        "pedidos_pendientes": pedidos_asignados.count(),
        "ultima_entrega": entregas_completadas.order_by("-fecha").first(),
    }
    return render(request, "usuarios/panel-conductor.html", context)


@login_required
def pedidos_conductor(request):
    conductor = request.user.usuario
    pedidos = Pedido.objects.filter(conductor=conductor).exclude(estado="entregado").select_related("usuario", "cliente__usuario")
    context = {"pedidos": pedidos}

    return render(request, "usuarios/pedidos_conductor.html", context)


@login_required
def mis_entregas(request):
    conductor = request.user.usuario
    entregas = Pedido.objects.filter(conductor=conductor, estado="entregado").select_related("usuario", "cliente__usuario").order_by(
        "-fecha_solicitud"
    )
    context = {"entregas": entregas}

    return render(request, "usuarios/mis-entregas.html", context)


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
        "ordenes_count": Pedido.objects.count(),
        "total_ventas": Pedido.objects.aggregate(total=Sum("total"))["total"] or 0,
        "entregados_count": Pedido.objects.filter(estado="entregado").count(),
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
        telefono = limpiar_telefono(request.POST.get("telefono"))
        tipo_documento = request.POST.get("tipo_documento")
        documento = limpiar_telefono(request.POST.get("documento"))
        email = request.POST.get("email")

        if "foto_perfil" in request.FILES:
            usuario.foto_perfil = request.FILES["foto_perfil"]

        usuario.nombres = nombres
        usuario.apellidos = apellidos
        usuario.telefono = telefono
        usuario.tipo_documento = tipo_documento
        usuario.documento = documento
        usuario.sincronizado = False
        usuario.save()

        if email:
            request.user.email = email
            request.user.save()

        messages.success(request, "Perfil actualizado correctamente.")

        if usuario.rol == "admin":
            return redirect("usuarios:perfil_admin")
        elif usuario.rol == "conductor":
            return redirect("usuarios:perfil_conductor")
        else:
            return redirect("clientes:perfil_cliente")

    context = {"usuario": usuario}

    return render(request, "usuarios/editar_perfil.html", context)


# =====================================================================
# GESTION DE USUARIOS
# =====================================================================


@login_required
def crear_usuario(request):
    if request.user.usuario.rol != "admin":
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"status": "error", "message": "No tienes permisos."}, status=403)
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("usuarios:panel")

    if request.method == "POST":
        nombres = request.POST.get("nombres")
        apellidos = request.POST.get("apellidos")
        email = request.POST.get("email")
        password = request.POST.get("password")
        telefono = limpiar_telefono(request.POST.get("telefono"))
        rol = request.POST.get("rol")
        tipo_doc = request.POST.get("tipo_doc")
        documento = limpiar_telefono(request.POST.get("documento"))

        if not all([nombres, apellidos, email, password, telefono, rol, tipo_doc, documento]):
            error_msg = "Todos los campos son obligatorios."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            context = {"form_data": request.POST, "action": "crear"}

            return render(request, "usuarios/form.html", context)

        if (
            User.objects.filter(email=email).exists()
            or User.objects.filter(username=email).exists()
        ):
            error_msg = "Este correo electrónico ya está registrado."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            context = {"form_data": request.POST, "action": "crear"}

            return render(request, "usuarios/form.html", context)

        try:
            with transaction.atomic():
                user = User(
                    username=email,
                    email=email,
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                    rol=rol,
                    tipo_documento=tipo_doc,
                    documento=documento,
                    estado="activo",
                    sincronizado=False,
                )
                user.set_password(password)
                user.save()
                if rol == "conductor":
                    Conductor.objects.get_or_create(
                        usuario=user,
                        defaults={
                            "numero_licencia": f"PEND-{user.id}",
                            "categoria_licencia": "N/A",
                            "fecha_vencimiento_licencia": now().date(),
                            "estado": "activo",
                        },
                    )
        except Exception as e:
            if "duplicate key" in str(e).lower() and conexion_remota_disponible():
                from django.db import connections

                try:
                    with connections["remota"].cursor() as cursor:
                        cursor.execute(
                            "SELECT setval(pg_get_serial_sequence('usuario', 'id'), (SELECT MAX(id) FROM usuario));"
                        )
                except Exception:
                    pass
                user = User(
                    username=email,
                    email=email,
                    nombres=nombres,
                    apellidos=apellidos,
                    telefono=telefono,
                    rol=rol,
                    tipo_documento=tipo_doc,
                    documento=documento,
                    estado="activo",
                    sincronizado=False,
                )
                user.set_password(password)
                user.save()
                if rol == "conductor":
                    Conductor.objects.get_or_create(
                        usuario=user,
                        defaults={
                            "numero_licencia": f"PEND-{user.id}",
                            "categoria_licencia": "N/A",
                            "fecha_vencimiento_licencia": now().date(),
                            "estado": "activo",
                        },
                    )
            else:
                raise e

        try:
            if "foto_perfil" in request.FILES:
                user.foto_perfil = request.FILES["foto_perfil"]
                user.save()

            registrar_actividad(
                request,
                "crear",
                "usuarios",
                user.id,
                f"Administrador creó usuario: {email} como {rol}",
            )

            success_msg = f"Usuario {nombres} creado correctamente."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "success", "message": success_msg})

            messages.success(request, success_msg)
            return redirect("usuarios:lista_usuarios")
        except Exception as e:
            error_msg = f"Error al crear usuario: {str(e)}"
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=500)

            messages.error(request, error_msg)
            context = {"error": error_msg, "form_data": request.POST, "action": "crear"}

            return render(request, "usuarios/form.html", context)

    context = {"action": "crear", "form_data": {}}

    return render(request, "usuarios/form.html", context)


@login_required
def lista_usuarios(request):
    query = request.GET.get("q")
    active_tab = request.GET.get("tab", "general")

    usuarios_list = buscar_usuarios_generales(query)

    admins = usuarios_list.filter(rol="admin")
    clientes = usuarios_list.filter(rol="cliente")
    conductores = usuarios_list.filter(rol="conductor")

    context = {
        "usuarios_todos": usuarios_list,
        "admins": admins,
        "clientes": clientes,
        "conductores": conductores,
        "query": query,
        "active_tab": active_tab,
    }

    return render(request, "usuarios/lista.html", context)


@login_required
def toggle_estado_usuario(request, id):
    if request.user.usuario.rol != "admin":
        messages.error(request, "No tienes permisos para realizar esta acción.")
        return redirect("usuarios:panel")

    usuario_obj = get_object_or_404(Usuario, id=id)

    if usuario_obj.user.username == "Edward_Fonseca":
        messages.error(request, "El Administrador Global no puede ser desactivado.")
        return redirect("usuarios:lista_usuarios")

    nuevo_estado = "inactivo" if usuario_obj.estado == "activo" else "activo"
    usuario_obj.estado = nuevo_estado
    usuario_obj.save()

    usuario_obj.user.is_active = nuevo_estado == "activo"
    usuario_obj.user.save()

    accion = "desactivado" if nuevo_estado == "inactivo" else "activado"
    registrar_actividad(
        request, "editar", "usuarios", id, f"Usuario {accion}: {usuario_obj.user.username}"
    )
    messages.success(request, f"Usuario {usuario_obj.user.username} {accion} correctamente.")
    return redirect("usuarios:lista_usuarios")


@login_required
def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)

    if request.user.usuario.rol != "admin":
        messages.error(request, "No tienes permiso para realizar esta acción.")
        return redirect("usuarios:lista_usuarios")

    usuario.delete()
    messages.success(request, f"Usuario {usuario.nombres} eliminado correctamente.")
    return redirect("usuarios:lista_usuarios")


@login_required
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)

    if request.user.usuario.rol != "admin" and request.user.usuario != usuario:
        messages.error(request, "No tienes permisos para editar este perfil.")
        return redirect("usuarios:panel")

    if usuario.user.username == "Edward_Fonseca" and request.user.username != "Edward_Fonseca":
        messages.error(request, "Solo el Administrador Global puede modificar su propia cuenta.")
        return redirect("usuarios:lista_usuarios")

    if request.method == "POST":
        nombres = request.POST.get("nombres")
        apellidos = request.POST.get("apellidos")
        telefono = limpiar_telefono(request.POST.get("telefono"))
        rol = request.POST.get("rol")

        if not all([nombres, apellidos, telefono]):
            messages.error(request, "Los campos nombres, apellidos y teléfono son obligatorios.")
            context = {"usuario": usuario, "form_data": request.POST, "action": "editar"}

            return render(request, "usuarios/form.html", context)

        try:
            usuario.nombres = nombres
            usuario.apellidos = apellidos
            usuario.telefono = telefono

            if "foto_perfil" in request.FILES:
                usuario.foto_perfil = request.FILES["foto_perfil"]

            if request.user.usuario.rol == "admin" and rol:
                usuario.rol = rol

            usuario.sincronizado = False
            usuario.save()
            if usuario.rol == "conductor":
                Conductor.objects.get_or_create(
                    usuario=usuario,
                    defaults={
                        "numero_licencia": f"PEND-{usuario.id}",
                        "categoria_licencia": "N/A",
                        "fecha_vencimiento_licencia": now().date(),
                        "estado": "activo",
                    },
                )
            registrar_actividad(
                request,
                "editar",
                "usuarios",
                usuario.user.id,
                f"Perfil de usuario editado: {usuario.user.username}",
            )
            messages.success(request, "Cambios guardados exitosamente.")
            return redirect("usuarios:lista_usuarios")
        except Exception as e:
            messages.error(request, f"Error al guardar los cambios: {str(e)}")
            context = {"usuario": usuario, "form_data": request.POST, "action": "editar"}

            return render(request, "usuarios/form.html", context)

    context = {"usuario": usuario, "form_data": {}, "action": "editar"}

    return render(request, "usuarios/form.html", context)


@admin_required
def lista_conductores(request):
    conductores = (
        Usuario.objects.filter(rol="conductor")
        .select_related("perfil_conductor")
        .prefetch_related(
            Prefetch(
                "perfil_conductor__asignaciones_vehiculo",
                queryset=ConductorVehiculo.objects.filter(fecha_fin__isnull=True).select_related(
                    "vehiculo"
                ),
                to_attr="asignaciones_activas",
            )
        )
    )
    context = {"conductores": conductores}

    return render(request, "usuarios/conductores_lista.html", context)


@admin_required
def asignar_vehiculo_conductor(request, conductor_id):
    usuario = get_object_or_404(Usuario, id=conductor_id, rol="conductor")
    conductor = usuario.conductor_profile
    if conductor is None:
        conductor, _ = Conductor.objects.get_or_create(
            usuario=usuario,
            defaults={
                "numero_licencia": f"PEND-{usuario.id}",
                "categoria_licencia": "N/A",
                "fecha_vencimiento_licencia": now().date(),
                "estado": "activo",
            },
        )
        messages.warning(
            request,
            "Se creó un perfil provisional para este conductor. Actualiza la licencia más adelante.",
        )

    vehiculo_actual = conductor.vehiculo_actual
    default_initial = {"vehiculo": vehiculo_actual.id_vehiculo} if vehiculo_actual else None

    if request.method == "POST":
        form = AsignarVehiculoForm(request.POST, conductor=conductor)
        if form.is_valid():
            vehiculo_seleccionado = form.cleaned_data["vehiculo"]
            try:
                with transaction.atomic():
                    if (
                        vehiculo_actual
                        and vehiculo_actual.id_vehiculo == vehiculo_seleccionado.id_vehiculo
                    ):
                        messages.info(request, "El conductor ya tiene asignado ese vehículo.")
                    else:
                        conductor.asignaciones_vehiculo.filter(fecha_fin__isnull=True).update(
                            fecha_fin=now()
                        )
                        ConductorVehiculo.objects.create(
                            conductor=conductor, vehiculo=vehiculo_seleccionado
                        )
                        messages.success(
                            request,
                            f"Vehículo {vehiculo_seleccionado.placa} asignado a {usuario.nombres} correctamente.",
                        )
                return redirect("usuarios:lista_conductores")
            except Exception as e:
                messages.error(request, f"No fue posible guardar la asignación: {str(e)}")
    else:
        form = AsignarVehiculoForm(conductor=conductor, initial=default_initial)

    historial = conductor.asignaciones_vehiculo.select_related("vehiculo").order_by(
        "-fecha_asignacion"
    )
    context = {
        "usuario": usuario,
        "conductor": conductor,
        "vehiculo_actual": vehiculo_actual,
        "form": form,
        "historial": historial,
    }

    return render(request, "usuarios/asignar_vehiculo_conductor.html", context)


@login_required
def perfil_conductor(request):
    conductor_id = request.GET.get("id")

    if conductor_id and request.user.usuario.rol == "admin":
        conductor = get_object_or_404(Usuario, id=conductor_id)
    else:
        try:
            conductor = request.user.usuario
        except Usuario.DoesNotExist:
            logout(request)
            return redirect("usuarios:login")

    pedidos = Pedido.objects.filter(conductor=conductor).select_related("usuario", "cliente__usuario")

    from apps.ordenes.models import Entrega

    try:
        from apps.usuarios.models import Conductor as ConductorPerfil

        conductor_perfil = ConductorPerfil.objects.get(usuario=conductor)
        ultima_entrega = (
            Entrega.objects.filter(conductor=conductor).select_related("vehiculo", "pedido").order_by("-fecha_salida").first()
        )
        vehiculo = ultima_entrega.vehiculo if ultima_entrega else None
    except Exception:
        vehiculo = None

    context = {"conductor": conductor, "pedidos": pedidos, "vehiculo": vehiculo}

    return render(request, "usuarios/perfil-conductor.html", context)


# =====================================================================
# RECUPERAR CONTRASEÑA
# =====================================================================


class CustomPasswordResetView(PasswordResetView):
    template_name = "usuarios/recuperar_password.html"
    email_template_name = "registration/password_reset_email.txt"
    html_email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("usuarios:password_reset_done")
    from_email = None

    def get_users(self, email):
        users = User.objects.filter(email__iexact=email, is_active=True)
        if not users:
            users = User.objects.filter(username__iexact=email, is_active=True)
        return users

    def form_valid(self, form):
        email = form.cleaned_data["email"]
        logger.info(f"[Password Reset] Solicitud para: {email}")
        return super().form_valid(form)


# =====================================================================
# CERRAR SECCION
# =====================================================================


def cerrar_sesion(request):
    if request.user.is_authenticated:
        from core.utils import clear_user_cache

        clear_user_cache(request.user.id)

        try:
            registrar_actividad(
                request,
                "logout",
                "usuarios",
                request.user.id,
                f"Cierre de sesión del usuario: {request.user.username}",
            )
        except Exception as e:
            if (
                "duplicate key" in str(e).lower()
                and "historial" in str(e).lower()
                and conexion_remota_disponible()
            ):
                try:
                    from django.db import connections

                    with connections["remota"].cursor() as cursor:
                        cursor.execute(
                            "SELECT setval('historial_actividad_id_seq', (SELECT MAX(id) FROM historial_actividad));"
                        )
                    registrar_actividad(
                        request,
                        "logout",
                        "usuarios",
                        request.user.id,
                        f"Cierre de sesión del usuario: {request.user.username}",
                    )
                except Exception:
                    pass
            else:
                pass
    logout(request)
    return redirect("usuarios:login")


# =====================================================================
# NOTIFICACIONES
# =====================================================================


@login_required
def lista_notificaciones(request):
    try:
        notificaciones = request.user.usuario.notificaciones.all().order_by("-fecha")
    except Usuario.DoesNotExist:
        notificaciones = []
    context = {"notificaciones": notificaciones}

    return render(request, "usuarios/notificaciones.html", context)


@login_required
def marcar_notificacion_leida(request, id):
    from django.utils.http import url_has_allowed_host_and_scheme

    try:
        notificacion = get_object_or_404(request.user.usuario.notificaciones, id=id)
        notificacion.leida = True
        notificacion.save(update_fields=["leida"])

        if notificacion.link and url_has_allowed_host_and_scheme(
            url=notificacion.link,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(notificacion.link)
    except Usuario.DoesNotExist:
        pass
    return redirect("usuarios:notificaciones")


@login_required
def configuraciones_usuario(request):
    try:
        usuario = request.user.usuario
    except Usuario.DoesNotExist:
        logout(request)
        return redirect("usuarios:login")

    if request.method == "POST":
        messages.success(request, "Configuraciones actualizadas correctamente.")
        return redirect("usuarios:configuraciones")

    context = {"usuario": usuario}

    return render(request, "usuarios/configuraciones.html", context)


@require_POST
def cambiar_modo_bd(request):
    """Alterna entre base de datos local (SQLite) y remota (Neon)."""
    modo = request.POST.get("modo", "").strip().lower()
    nuevo_modo = None
    mensaje_ok = None

    if modo not in (PREF_LOCAL, PREF_REMOTA):
        messages.error(request, "Modo de base de datos no válido.")
    elif modo == PREF_REMOTA:
        if "remota" not in settings.DATABASES:
            messages.error(
                request,
                "La base remota no está configurada. Define DATABASE_URL en tu archivo .env.",
            )
        elif not conexion_remota_disponible():
            messages.error(
                request,
                "No hay conexión con la base remota. Revisa tu internet o las credenciales de Neon.",
            )
        else:
            nuevo_modo = PREF_REMOTA
            mensaje_ok = "Remoto"
    else:
        if conexion_remota_disponible():
            try:
                sync_all_usuarios()
            except Exception as e:
                logger.error(f"Error sincronizando al cambiar a local: {e}")

        nuevo_modo = PREF_LOCAL
        mensaje_ok = "Local"

    if nuevo_modo:
        invalidate_connection_cache()
        if request.user.is_authenticated:
            logout(request)
        request.session["bd_preferida"] = nuevo_modo
        request.session.modified = True
        messages.success(request, mensaje_ok)
        response = redirect("usuarios:login")
        response.set_cookie(
            "bd_preferida", nuevo_modo, max_age=31536000, httponly=True, samesite="Lax"
        )
        return response

    destino = request.META.get("HTTP_REFERER") or reverse("usuarios:login")
    return redirect(destino)
