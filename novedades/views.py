from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.permissions import requiere_funcion
from ordenes.models import Entrega
from .models import Novedad, Seguimiento, RespuestaSeguimiento


@login_required
@requiere_funcion("registrar_novedad")
def crear_novedad(request, entrega_id):
    entrega = get_object_or_404(
        Entrega.objects.select_related("pedido"),
        pk=entrega_id,
    )
    if request.method == "POST":
        Novedad.objects.create(
            entrega=entrega,
            tipo=request.POST.get("tipo"),
            descripcion=request.POST.get("descripcion"),
            reportado_por=request.user,
        )
        messages.success(request, "Novedad registrada.")
        return redirect("ordenes:ver_pedido_admin", id=entrega.pedido_id)
    return render(
        request,
        "novedades/crear.html",
        {"entrega": entrega, "pedido": entrega.pedido},
    )


@login_required
def agregar_seguimiento(request, novedad_id):
    novedad = get_object_or_404(Novedad, pk=novedad_id)
    if request.method == "POST":
        Seguimiento.objects.create(
            novedad=novedad,
            atendido_por=request.user,
            comentario=request.POST.get("comentario"),
        )
        if novedad.estado == "abierta":
            novedad.estado = "en_atencion"
            novedad.save(update_fields=["estado"])
        return redirect("novedades:crear", entrega_id=novedad.entrega_id)
    return render(request, "novedades/seguimiento.html", {"novedad": novedad})


@login_required
@requiere_funcion("responder_seguimiento")
def responder_seguimiento(request, seguimiento_id):
    seg = get_object_or_404(Seguimiento, pk=seguimiento_id)
    if request.method == "POST":
        RespuestaSeguimiento.objects.create(
            seguimiento=seg,
            redactada_por=request.user,
            texto=request.POST.get("texto"),
            estado=request.POST.get("estado", "aceptada"),
        )
        seg.estado = "respondida"
        seg.save(update_fields=["estado"])
        if seg.novedad.estado == "en_atencion":
            seg.novedad.estado = "cerrada"
            seg.novedad.save(update_fields=["estado"])
        return redirect("ordenes:ver_pedido_admin", id=seg.novedad.entrega.pedido_id)
    return render(request, "novedades/responder.html", {"seguimiento": seg})