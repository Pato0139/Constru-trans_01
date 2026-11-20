from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import SugerenciaForm
from .models import (
    CategoriaAyuda,
    GuiaEdicion,
    ManualUsuario,
)


@login_required
def index_ayuda(request):
    """Página principal del módulo de ayuda."""
    manuales = ManualUsuario.objects.filter(activo=True)

    manuales_por_rol = {
        "admin": {
            "titulo": "Manual del Administrador",
            "archivo": "manuales/MANUAL ADMINISTRADOR.pdf",
            "descripcion": "Guía de uso del panel de administración y sus herramientas.",
        },
        "cliente": {
            "titulo": "Manual de Usuario",
            "archivo": "manuales/MANUAL USUARIO.pdf",
            "descripcion": "Guía para usar el panel de cliente, crear pedidos y consultar su estado.",
        },
        "conductor": {
            "titulo": "Manual del Conductor",
            "archivo": "manuales/MANUAL CONDUCTOR.pdf",
            "descripcion": "Guía del panel del conductor, las entregas y sus novedades.",
        },
    }
    manual_rol = manuales_por_rol.get(getattr(request.user, "rol", ""))

    context = {
        "manuales": manuales,
        "manual_rol": manual_rol,
    }
    return render(request, "ayuda/index.html", context)


@login_required
def lista_guias(request, categoria_id=None):
    """Lista de guías de edición."""
    guias = GuiaEdicion.objects.filter(activo=True)
    categoria = None

    if categoria_id:
        categoria = get_object_or_404(CategoriaAyuda, id=categoria_id)
        guias = guias.filter(categoria=categoria)

    categorias = CategoriaAyuda.objects.all()

    context = {
        "guias": guias,
        "categorias": categorias,
        "categoria_actual": categoria,
    }
    return render(request, "ayuda/lista_guias.html", context)


@login_required
def detalle_guia(request, guia_id):
    """Detalle de una guía de edición con sus pasos."""
    guia = get_object_or_404(GuiaEdicion, id=guia_id, activo=True)
    pasos = guia.pasos.all()

    context = {
        "guia": guia,
        "pasos": pasos,
    }
    return render(request, "ayuda/detalle_guia.html", context)


@login_required
def crear_sugerencia(request):
    """Crear una nueva sugerencia o recomendación."""
    if request.method == "POST":
        form = SugerenciaForm(request.POST)
        if form.is_valid():
            sugerencia = form.save(commit=False)
            sugerencia.usuario = request.user
            sugerencia.save()
            messages.success(request, "¡Tu sugerencia ha sido enviada exitosamente!")
            return redirect("ayuda:index")
    else:
        form = SugerenciaForm()

    context = {
        "form": form,
    }
    return render(request, "ayuda/crear_sugerencia.html", context)


