from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required


def inicio(request):
    if request.user.is_authenticated:
        try:
            usuario = request.user.usuario
            if usuario.rol == "admin":
                return redirect("usuarios:panel")
            elif usuario.rol == "cliente":
                return redirect("clientes:panel_cliente")
            elif usuario.rol == "conductor":
                return redirect("usuarios:panel_conductor")
        except Exception:
            pass
        return redirect("usuarios:panel")
    return redirect("usuarios:login")
