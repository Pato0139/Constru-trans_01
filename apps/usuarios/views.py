import logging
import smtplib

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

User = get_user_model()
from django.contrib.auth.views import PasswordResetView
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Prefetch, Q, Sum
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now

from apps.catalogo.models import MaterialConstruccion as Material
from apps.logistica.forms import AsignarVehiculoForm
from apps.logistica.models import ConductorVehiculo
from apps.pedidos.models import Pedido
from apps.usuarios.weather import get_route_weather
from config.db_preference import (
    PREF_LOCAL,
    PREF_REMOTA,
    get_db_preference,
    invalidate_connection_cache,
)
from config.security import (
    _respuesta_no_autorizada,
    admin_required,
    obtener_ip,
    registrar_evento,
    registrar_warning,
    role_required,
)
from config.superadmin_lock import es_superadmin_global
from config.sync import sync_all_usuarios
from config.utils import conexion_remota_disponible, registrar_actividad

from .forms import CustomPasswordResetForm, FotoPerfilForm, LoginForm, RegistroForm
from .models import Conductor, Usuario
from .utils import limpiar_documento, limpiar_telefono

logger = logging.getLogger(__name__)

LOGIN_REMEMBER_COOKIE = "constru_trans_login"
LOGIN_REMEMBER_SECONDS = 1209600

from django.core.signing import TimestampSigner, BadSignature

_REMEMBER_SIGNER = TimestampSigner(salt="constru-trans-remember")

def _crear_token_remember(user_id, session_version=0):
    """Crea un token firmado para la cookie remember-me."""
    return _REMEMBER_SIGNER.sign_object({"uid": int(user_id), "sv": int(session_version)})

def _verificar_token_remember(token, max_age=LOGIN_REMEMBER_SECONDS):
    """Verifica y decodifica el token remember-me. Retorna (user_id, session_version) o (None, None)."""
    try:
        obj = _REMEMBER_SIGNER.unsign_object(token, max_age=max_age)
        return obj.get("uid"), obj.get("sv", 0)
    except (BadSignature, KeyError, TypeError):
        return None, None

def _buscar_qs_por_rol(rol, query=None):
    qs = Usuario.objects.select_related("perfil_cliente").order_by("-id")
    if rol is not None:
        qs = qs.filter(rol=rol)
    if query:
        qs = qs.filter(
            Q(nombres__icontains=query) | Q(email__icontains=query) | Q(documento__icontains=query)
        )
    return qs


def _fusionar_listas_usuarios(qs_local, qs_remota):
    """Fusiona dos querysets/listas de usuarios evitando duplicados por id."""
    seen = set()
    merged = []
    for obj in list(qs_local) + list(qs_remota):
        if obj.id in seen:
            continue
        seen.add(obj.id)
        merged.append(obj)
    merged.sort(key=lambda u: u.id, reverse=True)
    return merged


def _lista_usuarios_unificada_por_rol(rol, query=None):
    """
    Devuelve la lista de usuarios unificada (local + remota si está disponible).

    Optimización anti-hang:
      - Si el usuario ya eligió PREF_LOCAL, NO consultamos remota (ya se salió de la nube).
      - Solo consultamos remota si NO hay PREF_LOCAL y hay caché positiva (para no
        disparar un TCP connect de 2s+ en cada request cuando la nube está offline).
    """
    from django.conf import settings
    from django.core.cache import cache

    qs_local = _buscar_qs_por_rol(rol, query).using("default")
    qs_remota = []

    preferencia_actual = get_db_preference()
    if preferencia_actual == PREF_LOCAL:
        return list(qs_local)

    remota_ok_cache = cache.get("core:conexion_remota_disponible")
    if remota_ok_cache is False:
        return list(qs_local)

    if "remota" not in settings.DATABASES:
        return list(qs_local)

    if remota_ok_cache is None:
        remota_disponible = conexion_remota_disponible()
    else:
        remota_disponible = remota_ok_cache

    if remota_disponible:
        try:
            qs_remota = list(_buscar_qs_por_rol(rol, query).using("remota"))
        except Exception:
            qs_remota = []

    return _fusionar_listas_usuarios(qs_local, qs_remota)


@admin_required
def lista_usuarios(request):
    query = request.GET.get("q")
    active_tab = request.GET.get("tab", "general")

    usuarios_todos = _lista_usuarios_unificada_por_rol(None, query)
    clientes = _lista_usuarios_unificada_por_rol("cliente", query)
    conductores = _lista_usuarios_unificada_por_rol("conductor", query)
    admins = _lista_usuarios_unificada_por_rol("admin", query)

    context = {
        "usuarios_todos": usuarios_todos,
        "clientes": clientes,
        "conductores": conductores,
        "admins": admins,
        "query": query,
        "active_tab": active_tab,
    }
    return render(request, "usuarios/lista.html", context)


def buscar_usuarios_generales(query=None):
    """
    Lógica unificada para buscar usuarios por nombre, email o documento.
    Optimizado con select_related para evitar N+1 en plantillas.
    Versión unificada (local + remota) para vistas que aún la usen.
    """
    return _lista_usuarios_unificada_por_rol(None, query)


def buscar_conductores(query=None):
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
        if not form.is_valid():
            error_msg = "Revise los datos ingresados e intente nuevamente."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "status": "error",
                        "message": error_msg,
                        "errors": {
                            field: [str(error) for error in errors]
                            for field, errors in form.errors.items()
                        },
                    },
                    status=400,
                )
            messages.error(request, error_msg)
            return render(request, "usuarios/registro.html", {"form": form}, status=400)

        data = form.cleaned_data
        nombres = data["nombres"]
        apellidos = data["apellidos"]
        correo = data["correo"].casefold()
        contrasena = data["contrasena"]
        telefono = data["telefono"]
        tipo_documento = data["tipo_documento"]
        documento = data["documento"]
        pais_codigo = data["pais_codigo"]

        try:
            telefono_completo = f"{pais_codigo}{telefono}"
            nuevo_usuario = User.objects.db_manager("default").create_user(
                username=correo,
                email=correo,
                password=contrasena,
                nombres=nombres,
                apellidos=apellidos,
                telefono=telefono_completo,
                rol="cliente",
                tipo_documento=tipo_documento,
                documento=documento,
                estado="activo",
                sincronizado=False,
            )

            # Cerrar cualquier sesión previa para evitar confusiones de rol (ej. admin previo)
            if request.user.is_authenticated:
                logout(request)

            # Iniciar sesión automáticamente con la nueva cuenta de cliente
            nuevo_usuario.backend = "apps.usuarios.backends.EmailOrUsernameBackend"
            login(request, nuevo_usuario)
            request.session["session_version"] = nuevo_usuario.session_version

            dest_url = reverse("clientes:panel_cliente")
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "status": "success",
                        "message": "¡Cuenta creada exitosamente! Bienvenido/a a Constru-trans.",
                        "redirect_url": dest_url,
                    }
                )
            messages.success(request, "¡Cuenta creada exitosamente! Bienvenido/a a Constru-trans.")
            return redirect(dest_url)

        except IntegrityError:
            logger.warning("Conflicto al registrar la cuenta %s", correo, exc_info=True)
            error_msg = (
                "No se pudo completar el registro. Verifique si el correo o documento ya existen."
            )
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            return render(request, "usuarios/registro.html", {"form": form}, status=400)
        except DatabaseError:
            logger.exception("Error de base de datos durante el registro de %s", correo)
            error_msg = "No fue posible completar el registro en este momento. Inténtelo más tarde."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=500)
            messages.error(request, error_msg)
            return render(request, "usuarios/registro.html", {"form": form}, status=500)

    # Si un usuario autenticado entra por GET a registrarse, cerramos la sesión previa
    if request.user.is_authenticated:
        logout(request)

    form = RegistroForm()
    context = {"form": form}
    return render(request, "usuarios/registro.html", context)


# =====================================================================
# LOGIN
# =====================================================================


def login_usuario(request):
    if request.user.is_authenticated:
        usuario = request.user
        if usuario.rol == "admin":
            return redirect("usuarios:panel")
        elif usuario.rol == "cliente":
            return redirect("clientes:panel_cliente")
        elif usuario.rol == "conductor":
            return redirect("usuarios:panel_conductor")
        return redirect("usuarios:panel")

    modo_local = not conexion_remota_disponible()

    if request.method == "POST":
        # Rate-limiting por IP: bloquear tras 10 intentos fallidos en 5 minutos
        from django.core.cache import cache
        ip = obtener_ip(request)
        rate_key = f"login_rate:{ip}"
        intentos_ip = cache.get(rate_key, 0)
        if intentos_ip >= 10:
            error_message = (
                "Demasiados intentos desde tu red. "
                "Espera 5 minutos antes de intentar novamente."
            )
            messages.error(request, error_message)
            context = {"modo_local": modo_local}
            return render(request, "usuarios/login.html", context)

        form = LoginForm(request.POST)
        if form.is_valid():
            identifier = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")

            user_obj = None
            try:
                user_obj = User.objects.get(username=identifier)
            except User.DoesNotExist:
                try:
                    user_obj = User.objects.get(email__iexact=identifier)
                except User.DoesNotExist:
                    pass

            if user_obj:
                if user_obj.esta_bloqueado():
                    tiempo_restante = user_obj.obtener_tiempo_restante_bloqueo()
                    error_message = (
                        f"Tu cuenta está bloqueada por {tiempo_restante}. "
                        "Intenta más tarde o contacta a soporte."
                    )
                    messages.error(request, error_message)
                    if request.headers.get("x-requested-with") == "XMLHttpRequest":
                        return JsonResponse(
                            {"status": "error", "message": error_message}, status=403
                        )
                    context = {"form": form, "modo_local": modo_local}
                    return render(request, "usuarios/login.html", context)

            # Usa EmailOrUsernameBackend primero (username O email); fallback por email luego.
            user = authenticate(request, username=identifier, password=password)

            if user is None and user_obj is not None:
                # Usuario existía pero authenticate devolvió None.
                # Determinamos la causa real para no penalizar (no contar intento fallido
                # si la contraseña SÍ era correcta y el problema es estado/is_active).
                password_correcto = user_obj.check_password(password)
                if password_correcto:
                    # Contraseña correcta, pero el usuario no pudo pasar por estado.
                    estado = getattr(user_obj, "estado", "activo")
                    is_active = getattr(user_obj, "is_active", True)
                    if estado != "activo" or not is_active:
                        if estado == "suspendido":
                            error_message = (
                                "Tu cuenta se encuentra suspendida. "
                                "Por favor contacta a soporte para más información."
                            )
                        elif estado == "inactivo" or not is_active:
                            error_message = (
                                "Tu cuenta está desactivada. "
                                "Por favor contacta a soporte para reactivarla."
                            )
                        else:
                            error_message = (
                                "Tu cuenta no está disponible actualmente. "
                                "Por favor contacta a soporte."
                            )
                        messages.error(request, error_message)
                        if request.headers.get("x-requested-with") == "XMLHttpRequest":
                            return JsonResponse(
                                {"status": "error", "message": error_message}, status=403
                            )
                        context = {"form": form, "modo_local": modo_local}
                        return render(request, "usuarios/login.html", context)
                else:
                    # Fallback: autenticar usando username del user_obj por si identifier
                    # fue email y backend fallback ModelBackend no acepta email directo.
                    user = authenticate(request, username=user_obj.username, password=password)

            if user is not None:
                user.reiniciar_intentos()
                if user.rol in {"cliente", "conductor"}:
                    user.ensure_profile_for_role()

                if not hasattr(user, "backend"):
                    user.backend = "apps.usuarios.backends.EmailOrUsernameBackend"

                login(request, user)
                request.session["session_version"] = user.session_version

                remember_me = form.cleaned_data.get("remember_me")
                if remember_me:
                    request.session.set_expiry(LOGIN_REMEMBER_SECONDS)
                else:
                    request.session.set_expiry(0)

                try:
                    registrar_actividad(
                        request, "login", "usuarios", user.id, f"Inicio de sesión: {user.username}"
                    )
                except IntegrityError as exc:
                    logger.warning("Conflicto historial en login de %s: %s", user.username, exc)
                except Exception as exc:
                    logger.error("Fallo registrando actividad de login: %s", exc)

                messages.success(request, f"¡Bienvenido de nuevo, {user.nombres}!")

                next_url = request.GET.get("next")
                redirect_target = (
                    next_url
                    if next_url
                    and url_has_allowed_host_and_scheme(
                        url=next_url,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure(),
                    )
                    else (
                        "usuarios:panel"
                        if user.rol == "admin"
                        else "clientes:panel_cliente"
                        if user.rol == "cliente"
                        else "usuarios:panel_conductor"
                        if user.rol == "conductor"
                        else "usuarios:panel"
                    )
                )

                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    response = JsonResponse(
                        {
                            "status": "success",
                            "message": f"¡Bienvenido de nuevo, {user.nombres}!",
                            "redirect_url": reverse(redirect_target),
                        }
                    )
                else:
                    response = redirect(redirect_target)

                if remember_me:
                    response.set_cookie(
                        LOGIN_REMEMBER_COOKIE,
                        _crear_token_remember(user.pk, user.session_version),
                        max_age=LOGIN_REMEMBER_SECONDS,
                        secure=request.is_secure(),
                        httponly=True,
                        samesite="Lax",
                    )
                else:
                    response.delete_cookie(LOGIN_REMEMBER_COOKIE, samesite="Lax")

                return response
            else:
                error_message = "Usuario o contraseña incorrectos."
                # Incrementar contador de intentos fallidos por IP
                from django.core.cache import cache
                cache.set(rate_key, intentos_ip + 1, 300)
                if user_obj:
                    user_obj.registrar_intento_fallido()
                    if user_obj.esta_bloqueado():
                        tiempo_restante = user_obj.obtener_tiempo_restante_bloqueo()
                        error_message = f"Demasiados intentos fallidos. Tu cuenta está bloqueada por {tiempo_restante}."
                        messages.error(request, error_message)
                    else:
                        intentos_restantes = (
                            3 - user_obj.intentos_fallidos if user_obj.intentos_fallidos < 3 else 0
                        )
                        if intentos_restantes > 0:
                            error_message = f"Usuario o contraseña incorrectos. Te quedan {intentos_restantes} intento(s)."
                            messages.error(request, error_message)
                        else:
                            messages.error(request, error_message)
                else:
                    messages.error(request, error_message)

                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({"status": "error", "message": error_message}, status=400)
        else:
            error_message = "Por favor corrige los errores en el formulario."
            for field, errors in form.errors.items():
                for error in errors:
                    error_message = f"{field}: {error}"
                    messages.error(request, error_message)

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                errors_dict = {}
                for field, error_list in form.errors.items():
                    errors_dict[field] = [str(error) for error in error_list]
                return JsonResponse(
                    {
                        "status": "error",
                        "message": error_message,
                        "errors": errors_dict,
                    },
                    status=400,
                )

    else:
        form = LoginForm(initial={"username": request.COOKIES.get(LOGIN_REMEMBER_COOKIE, "")})

    context = {"form": form, "modo_local": modo_local}
    return render(request, "usuarios/login.html", context)


# =====================================================================
# PANEL ADMIND
# =====================================================================


@login_required
def panel(request):
    usuario = request.user

    if usuario.rol == "admin":
        from django.core.cache import cache

        from config.utils import get_cache_key

        cache_key = get_cache_key("panel_admin_v2", usuario.id)
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


@role_required(["conductor"])
def panel_conductor(request):
    conductor, _ = Conductor.ensure_for_user(request.user)
    pedidos_asignados = (
        Pedido.objects.filter(conductor=conductor)
        .select_related("usuario", "cliente__usuario")
        .exclude(estado="entregado")
    )
    proxima_entrega = (
        pedidos_asignados.exclude(estado=Pedido.CANCELADO)
        .order_by("fecha_entrega_programada", "fecha_solicitud")
        .first()
    )
    context = {
        "pedidos": pedidos_asignados,
        "proxima_entrega": proxima_entrega,
        "clima_ruta": (
            get_route_weather(
                proxima_entrega.direccion_destino,
                proxima_entrega.fecha_entrega_programada,
            )
            if proxima_entrega
            else None
        ),
    }
    return render(request, "usuarios/panel-conductor.html", context)


@role_required(["conductor"])
def pedidos_conductor(request):
    conductor, _ = Conductor.ensure_for_user(request.user)
    pedidos = (
        Pedido.objects.filter(conductor=conductor)
        .exclude(estado="entregado")
        .select_related("usuario", "cliente__usuario")
    )

    id_pedido = request.GET.get("id_pedido")
    origen = request.GET.get("origen")
    destino = request.GET.get("destino")
    fecha = request.GET.get("fecha")
    estado = request.GET.get("estado")

    if id_pedido:
        pedidos = pedidos.filter(codigo_pedido__icontains=id_pedido)
    if origen:
        pedidos = pedidos.filter(direccion_origen__icontains=origen)
    if destino:
        pedidos = pedidos.filter(direccion_destino__icontains=destino)
    if fecha:
        pedidos = pedidos.filter(fecha_solicitud__date=fecha)
    if estado:
        pedidos = pedidos.filter(estado=estado)

    context = {
        "pedidos": pedidos,
        "estados": Pedido.ESTADOS,
        "id_pedido": id_pedido,
        "origen": origen,
        "destino": destino,
        "fecha": fecha,
        "estado": estado,
    }
    return render(request, "usuarios/pedidos_conductor.html", context)


@role_required(["conductor"])
def mis_entregas(request):
    conductor, _ = Conductor.ensure_for_user(request.user)
    entregas = (
        Pedido.objects.filter(conductor=conductor)
        .select_related("usuario", "cliente__usuario")
        .order_by("-fecha_solicitud")
    )

    id_pedido = request.GET.get("id_pedido")
    origen = request.GET.get("origen")
    destino = request.GET.get("destino")
    fecha = request.GET.get("fecha")
    estado = request.GET.get("estado")

    if id_pedido:
        entregas = entregas.filter(codigo_pedido__icontains=id_pedido)
    if origen:
        entregas = entregas.filter(direccion_origen__icontains=origen)
    if destino:
        entregas = entregas.filter(direccion_destino__icontains=destino)
    if fecha:
        entregas = entregas.filter(fecha_solicitud__date=fecha)
    if estado:
        entregas = entregas.filter(estado=estado)

    context = {
        "entregas": entregas,
        "estados": Pedido.ESTADOS,
        "id_pedido": id_pedido,
        "origen": origen,
        "destino": destino,
        "fecha": fecha,
        "estado": estado,
    }
    return render(request, "usuarios/mis-entregas.html", context)


@login_required
def perfil_admin(request):
    usuario = request.user

    try:
        materiales_count = Material.objects.count()
    except Exception as exc:
        logger.warning("No se pudo contar MaterialConstruccion: %s", exc)
        materiales_count = 0

    context = {
        "usuario": usuario,
        "usuarios_count": Usuario.objects.count(),
        "materiales_count": materiales_count,
        "ordenes_count": Pedido.objects.count(),
        "total_ventas": Pedido.objects.aggregate(total=Sum("total"))["total"] or 0,
        "entregados_count": Pedido.objects.filter(estado="entregado").count(),
    }
    return render(request, "usuarios/detalle.html", context)


@login_required
def editar_perfil(request):
    usuario = request.user

    if request.method == "POST":
        if request.POST.get("action") == "upload_photo":
            foto_form = FotoPerfilForm(request.POST, request.FILES)
            if not foto_form.is_valid():
                messages.error(
                    request,
                    "No se pudo guardar la foto. Revisa el formato y el tamaño (máximo 5 MB).",
                )
                return render(
                    request,
                    "usuarios/editar_perfil.html",
                    {"usuario": usuario, "foto_form": foto_form},
                )

            foto_nueva = foto_form.cleaned_data["foto_perfil"]
            if not foto_nueva:
                messages.error(request, "Selecciona una foto antes de guardarla.")
                return redirect("usuarios:editar_perfil")

            foto_anterior = usuario.foto_perfil
            nombre_foto_anterior = foto_anterior.name if foto_anterior else ""
            usuario.foto_perfil = foto_nueva
            try:
                usuario.save(update_fields=["foto_perfil"])
            except (OSError, DatabaseError):
                nombre_foto_nuevo = usuario.foto_perfil.name
                if nombre_foto_nuevo and nombre_foto_nuevo != nombre_foto_anterior:
                    try:
                        usuario.foto_perfil.storage.delete(nombre_foto_nuevo)
                    except OSError as exc:
                        logger.warning(
                            "No se pudo limpiar la foto sin guardar del usuario %s: %s",
                            usuario.pk,
                            exc,
                        )
                usuario.foto_perfil.name = nombre_foto_anterior
                logger.exception("No se pudo guardar la foto de perfil del usuario %s", usuario.pk)
                messages.error(request, "No se pudo guardar la foto. Inténtalo de nuevo.")
                return redirect("usuarios:editar_perfil")

            if nombre_foto_anterior and nombre_foto_anterior != usuario.foto_perfil.name:
                try:
                    foto_anterior.storage.delete(nombre_foto_anterior)
                except OSError as exc:
                    logger.warning(
                        "No se pudo borrar la foto anterior del usuario %s: %s",
                        usuario.pk,
                        exc,
                    )

            messages.success(request, "La foto de perfil se guardó correctamente.")
            return redirect("usuarios:editar_perfil")

        foto_form = FotoPerfilForm(request.POST, request.FILES)
        if not foto_form.is_valid():
            messages.error(
                request, "No se pudo guardar la foto. Revisa el formato y el tamaño (máximo 5 MB)."
            )
            return render(
                request,
                "usuarios/editar_perfil.html",
                {"usuario": usuario, "foto_form": foto_form, "form_data": request.POST},
            )

        nombres = request.POST.get("nombres")
        apellidos = request.POST.get("apellidos")
        telefono = limpiar_telefono(request.POST.get("telefono"))
        email = (request.POST.get("email") or "").strip().casefold()
        nombres = (nombres or "").strip()
        apellidos = (apellidos or "").strip()

        if (
            not nombres
            or not apellidos
            or len(nombres) > 200
            or len(apellidos) > 200
            or len(telefono or "") > 20
        ):
            messages.error(request, "Revisa los nombres, apellidos y teléfono.")
            return render(
                request,
                "usuarios/editar_perfil.html",
                {"usuario": usuario, "foto_form": FotoPerfilForm()},
                status=400,
            )
        if email:
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, "El correo electrónico no es válido.")
                return render(
                    request,
                    "usuarios/editar_perfil.html",
                    {"usuario": usuario, "foto_form": FotoPerfilForm()},
                    status=400,
                )
            if User.objects.filter(
                Q(username__iexact=email) | Q(email__iexact=email)
            ).exclude(pk=usuario.pk).exists():
                messages.error(request, "Ese correo ya está asociado a otra cuenta.")
                return render(
                    request,
                    "usuarios/editar_perfil.html",
                    {"usuario": usuario, "foto_form": FotoPerfilForm()},
                    status=400,
                )
        foto_anterior = usuario.foto_perfil
        nombre_foto_anterior = foto_anterior.name if foto_anterior else ""

        foto_nueva = foto_form.cleaned_data.get("foto_perfil")
        if foto_nueva:
            usuario.foto_perfil = foto_nueva

        usuario.nombres = nombres
        usuario.apellidos = apellidos
        usuario.telefono = telefono
        usuario.sincronizado = False

        if email:
            usuario.email = email
            usuario.username = email

        try:
            usuario.save()
            if foto_nueva and nombre_foto_anterior:
                try:
                    foto_anterior.storage.delete(nombre_foto_anterior)
                except OSError as exc:
                    logger.warning(
                        "No se pudo borrar la foto anterior del usuario %s: %s", usuario.pk, exc
                    )
            messages.success(request, "Perfil actualizado correctamente.")
        except IntegrityError:
            if foto_nueva and usuario.foto_perfil.name != nombre_foto_anterior:
                usuario.foto_perfil.storage.delete(usuario.foto_perfil.name)
                usuario.foto_perfil.name = nombre_foto_anterior
            messages.error(
                request, "No se pudo actualizar el perfil porque el correo ya está en uso."
            )
            return render(
                request,
                "usuarios/editar_perfil.html",
                {"usuario": usuario, "foto_form": foto_form, "form_data": request.POST},
            )

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


@admin_required
def crear_usuario(request):
    if request.method == "POST":
        nombres = (request.POST.get("nombres") or "").strip()
        apellidos = (request.POST.get("apellidos") or "").strip()
        email = (request.POST.get("email") or "").strip().casefold()
        password = request.POST.get("password") or ""
        telefono = limpiar_telefono(request.POST.get("telefono"))
        rol = request.POST.get("rol")
        tipo_doc = request.POST.get("tipo_doc")
        documento = limpiar_documento(request.POST.get("documento"))
        form_data = request.POST.copy()
        form_data.pop("password", None)

        if rol == "admin" and not es_superadmin_global(request.user):
            raise PermissionDenied(
                "Solo el Administrador Global puede crear otros administradores."
            )

        logger.info(f"Intentando crear usuario: {email}, rol: {rol}")

        # Validación básica simplificada
        if not all([nombres, apellidos, email, password, telefono, rol, tipo_doc, documento]):
            error_msg = "Todos los campos son obligatorios."
            logger.warning("Campos incompletos")
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            context = {"form_data": form_data, "action": "crear"}
            return render(request, "usuarios/form.html", context)

        try:
            validate_email(email)
            validate_password(password)
            if (
                len(nombres) > 200
                or len(apellidos) > 200
                or len(email) > 150
                or not 7 <= len(telefono) <= 15
                or not 7 <= len(documento) <= 15
                or (tipo_doc == "PA" and not documento.isalnum())
                or (tipo_doc != "PA" and not documento.isdigit())
                or rol not in dict(Usuario.ROLES)
                or tipo_doc not in dict(Usuario.TIPOS_DOCUMENTO)
                or User.objects.using("default").filter(
                    Q(email__iexact=email) | Q(username__iexact=email)
                ).exists()
            ):
                raise ValidationError("Los datos exceden los límites o contienen opciones no válidas.")
        except ValidationError:
            messages.error(request, "Revisa el correo, contraseña, documento y rol seleccionados.")
            return render(
                request,
                "usuarios/form.html",
                {"form_data": form_data, "action": "crear"},
                status=400,
            )

        foto_form = FotoPerfilForm(request.POST, request.FILES)
        if not foto_form.is_valid():
            messages.error(request, "La foto debe ser una imagen válida de hasta 5 MB.")
            return render(
                request,
                "usuarios/form.html",
                {"form_data": form_data, "action": "crear"},
                status=400,
            )

        try:
            # Creación directa de usuario - MÁS SIMPLE POSIBLE
            logger.info(f"Creando usuario directamente: {email}")
            user = User.objects.db_manager("default").create_user(
                username=email,
                email=email,
                password=password,
                nombres=nombres,
                apellidos=apellidos,
                telefono=telefono,
                rol=rol,
                tipo_documento=tipo_doc,
                documento=documento,
                estado="activo",
                sincronizado=False,
            )
            logger.info(f"Usuario creado exitosamente: {user.id}")

            # Crear perfil de conductor si es necesario (sin transacción)
            if rol == "conductor":
                try:
                    logger.info(f"Creando perfil de conductor para: {email}")
                    Conductor.objects.create(
                        usuario=user,
                        numero_licencia=f"PEND-{user.id}",
                        categoria_licencia="N/A",
                        fecha_vencimiento_licencia=now().date(),
                        estado="activo",
                    )
                    logger.info("Perfil de conductor creado")
                except IntegrityError as exc:
                    logger.warning("Perfil conductor no creado por conflicto: %s", exc)

            # Foto de perfil si existe
            foto_perfil = foto_form.cleaned_data.get("foto_perfil")
            if foto_perfil:
                user.foto_perfil = foto_perfil
                user.save()

            # RESPUESTA INMEDIATA sin registrar actividad
            success_msg = f"Usuario {nombres} creado correctamente."
            logger.info(f"Proceso completado exitosamente para: {email}")

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "success", "message": success_msg})

            messages.success(request, success_msg)
            return redirect("usuarios:lista_usuarios")

        except IntegrityError as exc:
            logger.warning("Conflicto creando usuario %s: %s", email, exc)
            error_msg = "Ya existe un usuario con esos datos."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            context = {"error": error_msg, "form_data": form_data, "action": "crear"}
            return render(request, "usuarios/form.html", context)
        except Exception as e:
            logger.error("Error creando usuario %s: %s", email, e, exc_info=True)
            error_msg = "No se pudo crear el usuario. Revisa los datos e inténtalo nuevamente."
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"status": "error", "message": error_msg}, status=500)
            messages.error(request, error_msg)
            context = {"error": error_msg, "form_data": form_data, "action": "crear"}
            return render(request, "usuarios/form.html", context)

    context = {"action": "crear", "form_data": {}}
    return render(request, "usuarios/form.html", context)


@admin_required
@require_POST
def toggle_estado_usuario(request, id):
    usuario_obj = get_object_or_404(Usuario, id=id)

    if usuario_obj.es_superadmin:
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


@admin_required
@require_POST
def eliminar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)

    if usuario.es_superadmin:
        messages.error(request, "El Administrador Global no puede eliminarse desde aquí.")
        return redirect("usuarios:lista_usuarios")

    usuario.delete()
    messages.success(request, f"Usuario {usuario.nombres} eliminado correctamente.")
    return redirect("usuarios:lista_usuarios")


@login_required
def editar_usuario(request, id):
    usuario = get_object_or_404(Usuario, id=id)
    user = request.user

    is_super = es_superadmin_global(user)
    es_admin = is_super or user.rol == "admin"
    es_propio = user.id == usuario.user.id or user.pk == usuario.pk

    if not is_super:
        if usuario.es_superadmin and not es_propio:
            registrar_warning(obtener_ip(request))
            registrar_evento(
                request,
                "role_violation",
                gravedad="high",
                detalles={"target_user_id": usuario.id, "operacion": "editar_superadmin"},
            )
            return _respuesta_no_autorizada(
                request,
                detalles={
                    "operacion": "editar_usuario",
                    "target": usuario.id,
                    "motivo": "Solo el Administrador Global puede modificar su propia cuenta.",
                },
            )

    if not (es_admin or es_propio):
        registrar_warning(obtener_ip(request))
        registrar_evento(
            request,
            "role_violation",
            gravedad="high",
            detalles={"target_user_id": usuario.id, "operacion": "editar_ajeno"},
        )
        return _respuesta_no_autorizada(
            request,
            detalles={
                "rol_requerido": ["admin"],
                "rol_usuario": user.rol,
                "operacion": "editar_usuario",
                "permiso_alternativo": "propietario del perfil",
            },
        )

    if request.method == "POST":
        nombres = request.POST.get("nombres")
        apellidos = request.POST.get("apellidos")
        telefono = limpiar_telefono(request.POST.get("telefono"))
        rol = request.POST.get("rol")

        if not all([nombres, apellidos, telefono]):
            messages.error(request, "Los campos nombres, apellidos y teléfono son obligatorios.")
            context = {"usuario": usuario, "form_data": request.POST, "action": "editar"}
            return render(request, "usuarios/form.html", context)

        if (
            es_admin
            and rol
            and not is_super
            and (usuario.rol == "admin" or rol == "admin")
            and rol != usuario.rol
        ):
            raise PermissionDenied(
                "Solo el Administrador Global puede asignar o cambiar el rol de administrador."
            )
        if es_admin and rol and rol not in dict(Usuario.ROLES):
            messages.error(request, "El rol seleccionado no es válido.")
            return render(
                request,
                "usuarios/form.html",
                {"usuario": usuario, "action": "editar"},
                status=400,
            )

        try:
            foto_form = FotoPerfilForm(request.POST, request.FILES)
            if not foto_form.is_valid():
                messages.error(request, "La foto debe ser una imagen válida de hasta 5 MB.")
                return render(
                    request,
                    "usuarios/form.html",
                    {"usuario": usuario, "action": "editar"},
                    status=400,
                )
            usuario.nombres = nombres
            usuario.apellidos = apellidos
            usuario.telefono = telefono

            foto_perfil = foto_form.cleaned_data.get("foto_perfil")
            if foto_perfil:
                if usuario.foto_perfil:
                    try:
                        usuario.foto_perfil.delete(save=False)
                    except OSError as exc:
                        logger.warning("No se pudo borrar foto anterior: %s", exc)
                usuario.foto_perfil = foto_perfil

            if es_admin and rol:
                usuario.rol = rol

            usuario.sincronizado = False
            usuario.save()
            if usuario.rol == "conductor":
                Conductor.ensure_for_user(usuario)
            registrar_actividad(
                request,
                "editar",
                "usuarios",
                usuario.user.id,
                f"Perfil de usuario editado: {usuario.user.username}",
            )
            messages.success(request, "Cambios guardados exitosamente.")
            return redirect("usuarios:lista_usuarios")
        except IntegrityError as exc:
            logger.warning("Conflicto editando usuario %s: %s", usuario.user.username, exc)
            messages.error(request, "Conflicto al guardar: revisa los datos únicos.")
            context = {"usuario": usuario, "form_data": request.POST, "action": "editar"}
            return render(request, "usuarios/form.html", context)
        except Exception as e:
            logger.error("Error editando usuario %s: %s", usuario.user.username, e, exc_info=True)
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
        conductor, _ = Conductor.ensure_for_user(usuario)
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
                logger.error("Error asignando vehículo: %s", e, exc_info=True)
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
@role_required(["admin", "conductor"])
def perfil_conductor(request):
    conductor_id = request.GET.get("id")

    if conductor_id and request.user.rol == "admin":
        usuario_conductor = get_object_or_404(Usuario, id=conductor_id)
    else:
        usuario_conductor = request.user

    perfil_conductor, _ = Conductor.ensure_for_user(usuario_conductor)
    pedidos = Pedido.objects.filter(conductor=perfil_conductor).select_related(
        "usuario", "cliente__usuario"
    )

    from apps.logistica.models import Entrega

    try:
        ultima_entrega = (
            Entrega.objects.filter(conductor=perfil_conductor)
            .select_related("vehiculo", "pedido")
            .order_by("-fecha_salida")
            .first()
        )
        vehiculo = ultima_entrega.vehiculo if ultima_entrega else None
    except Conductor.DoesNotExist:
        vehiculo = None
    except Exception as exc:
        logger.warning("Fallo cargando perfil de conductor: %s", exc)
        vehiculo = None

    context = {
        "conductor": usuario_conductor,
        "pedidos": pedidos,
        "vehiculo": vehiculo,
    }
    return render(request, "usuarios/perfil-conductor.html", context)


# =====================================================================
# RECUPERAR CONTRASEÑA
# =====================================================================
class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = "usuarios/recuperar_password.html"
    email_template_name = "registration/password_reset_email.txt"
    html_email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("usuarios:password_reset_done")
    from_email = None

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except (smtplib.SMTPException, OSError, requests.RequestException) as exc:
            logger.warning(
                "Password reset email delivery failed (%s)",
                type(exc).__name__,
            )
            form.add_error(
                None,
                "No pudimos enviar el correo de recuperación. Intenta de nuevo más tarde.",
            )
            return self.form_invalid(form)


# =====================================================================
# CERRAR SESIÓN
# =====================================================================
@csrf_protect
@require_POST
def cerrar_sesion(request):
    if request.user.is_authenticated:
        from config.utils import clear_user_cache

        clear_user_cache(request.user.id)

        try:
            registrar_actividad(
                request,
                "logout",
                "usuarios",
                request.user.id,
                f"Cierre de sesión del usuario: {request.user.username}",
            )
        except IntegrityError as exc:
            logger.warning("Conflicto historial logout: %s", exc)
        except Exception as e:
            logger.error("Fallo registrando logout: %s", e)

    logout(request)
    return redirect("usuarios:login")


# =====================================================================
# NOTIFICACIONES
# =====================================================================
@login_required
def lista_notificaciones(request):
    notificaciones = request.user.notificaciones.all().order_by("-fecha")
    context = {"notificaciones": notificaciones}
    return render(request, "usuarios/notificaciones.html", context)


@login_required
@require_POST
def marcar_notificacion_leida(request, id):
    from django.utils.http import url_has_allowed_host_and_scheme

    try:
        notificacion = get_object_or_404(request.user.notificaciones, id=id)
        notificacion.leida = True
        notificacion.save(update_fields=["leida"])

        if notificacion.link and url_has_allowed_host_and_scheme(
            url=notificacion.link,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(notificacion.link)
    except Exception as exc:
        logger.warning("No se pudo marcar notificación: %s", exc)
    return redirect("usuarios:notificaciones")


@login_required
def configuraciones_usuario(request):
    usuario = request.user
    if request.method == "POST":
        messages.success(request, "Configuraciones actualizadas correctamente.")
        return redirect("usuarios:configuraciones")
    context = {"usuario": usuario}
    return render(request, "usuarios/configuraciones.html", context)


@admin_required
@require_POST
def cambiar_modo_bd(request):
    """Alterna entre base de datos local (SQLite) y remota (Neon).

    NOTA: La sincronización completa NO ocurre dentro del request HTTP (para no
    bloquear 30s+). El usuario debe correr: `python manage.py sincronizar` o
    `python manage.py sync_all_usuarios` después de cambiar de modo.
    """
    modo = request.POST.get("modo", "").strip().lower()
    nuevo_modo = None
    mensaje_ok = None
    sincronizacion_pendiente = False

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
            mensaje_ok = "Cambiado a modo Remoto (Neon)."
    else:
        nuevo_modo = PREF_LOCAL
        mensaje_ok = "Cambiado a modo Local (SQLite)."
        if "remota" in settings.DATABASES and conexion_remota_disponible():
            sincronizacion_pendiente = True

    if nuevo_modo:
        invalidate_connection_cache()
        try:
            cache.clear()
        except Exception:
            pass

        if request.user.is_authenticated:
            logout(request)
        request.session["bd_preferida"] = nuevo_modo
        request.session.modified = True
        messages.success(request, mensaje_ok)
        if sincronizacion_pendiente:
            messages.warning(
                request,
                "Sincronización sugerida: ejecuta `python manage.py sincronizar` "
                "para llevar los datos de la nube a la base local.",
            )
        response = redirect("usuarios:login")
        response.set_cookie(
            "bd_preferida", nuevo_modo, max_age=31536000, httponly=True, samesite="Lax"
        )
        return response

    destino = request.META.get("HTTP_REFERER") or reverse("usuarios:login")
    return redirect(destino)
