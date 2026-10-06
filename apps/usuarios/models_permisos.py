from django.contrib.auth.models import Group, Permission as AuthPermission
from django.contrib.contenttypes.models import ContentType
from django.db import models
from .models import Usuario, Rol


class RolProxy(Group):
    class Meta:
        proxy = True
        verbose_name = "Rol de seguridad"
        verbose_name_plural = "Roles de seguridad"


class Permiso(models.Model):
    FUNCIONES = [
        ("aprobar_pedido",       "Aprobar pedido"),
        ("asignar_vehiculo",     "Asignar vehículo"),
        ("registrar_novedad",    "Registrar novedad"),
        ("responder_seguimiento","Responder seguimiento"),
        ("anular_factura",       "Anular factura"),
        ("registrar_pago",       "Registrar pago"),
        ("autorizar_despacho",   "Autorizar despacho"),
        ("gestionar_inventario", "Gestionar inventario"),
        ("gestionar_proveedor",  "Gestionar proveedor"),
        ("ver_bitacora",         "Ver bitácora"),
    ]
    id_permiso = models.BigAutoField(primary_key=True)
    codename = models.CharField(max_length=100, unique=True)
    nombre = models.CharField(max_length=150)
    funcion = models.CharField(max_length=60, choices=FUNCIONES)
    class Meta:
        db_table = "permiso"
        verbose_name = "Permiso"
        verbose_name_plural = "Permisos"
        ordering = ["funcion", "codename"]
    def __str__(self):
        return f"{self.funcion} ({self.codename})"


class UsuarioRolNegocio(models.Model):
    id_usuario_rol = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="roles_negocio")
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name="usuarios_negocio")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_revocacion = models.DateTimeField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    class Meta:
        db_table = "usuario_rol_negocio"
        unique_together = [("usuario", "rol")]
    def __str__(self):
        return f"{self.usuario} <- {self.rol}"


class RolPermiso(models.Model):
    id_rol_permiso = models.BigAutoField(primary_key=True)
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name="permisos_negocio")
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE, related_name="roles_negocio")
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "rol_permiso_negocio"
        unique_together = [("rol", "permiso")]
    def __str__(self):
        return f"{self.rol} <- {self.permiso}"


class PermisoUsuario(models.Model):
    id_permiso_usuario = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="permisos_directos")
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE, related_name="usuarios_directos")
    fecha_otorgado = models.DateTimeField(auto_now_add=True)
    vigente_hasta = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "permiso_usuario"
        unique_together = [("usuario", "permiso")]
    def __str__(self):
        return f"{self.usuario} <- {self.permiso}"


def usuario_tiene_permiso(user, funcion: str) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    try:
        if PermisoUsuario.objects.filter(usuario=user, permiso__funcion=funcion).exists():
            return True
    except Exception:
        pass
    try:
        roles = UsuarioRolNegocio.objects.filter(usuario=user, activo=True).values_list("rol_id", flat=True)
        if roles and RolPermiso.objects.filter(rol_id__in=roles, permiso__funcion=funcion).exists():
            return True
    except Exception:
        pass
    return False