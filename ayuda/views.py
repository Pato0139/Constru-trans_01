from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import (
    CategoriaAyuda,
    GuiaEdicion,
    PasoGuia,
    SugerenciaRecomendacion,
    ManualUsuario,
    ColorSistema,
)
from .forms import SugerenciaForm


@login_required
def index_ayuda(request):
    """Página principal del módulo de ayuda."""
    categorias = CategoriaAyuda.objects.all()
    guias_favoritas = GuiaEdicion.objects.filter(es_favorito=True, activo=True)[:5]
    ultimas_guias = GuiaEdicion.objects.filter(activo=True).order_by("-fecha_actualizacion")[:5]
    colores = ColorSistema.objects.filter(activo=True)
    manuales = ManualUsuario.objects.filter(activo=True)

    context = {
        "categorias": categorias,
        "guias_favoritas": guias_favoritas,
        "ultimas_guias": ultimas_guias,
        "colores": colores,
        "manuales": manuales,
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


@login_required
def lista_colores(request):
    """Lista de colores del sistema."""
    colores = ColorSistema.objects.filter(activo=True)
    context = {
        "colores": colores,
    }
    return render(request, "ayuda/lista_colores.html", context)
