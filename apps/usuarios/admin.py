from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import (
    EPS,
    Catalogo,
    Conductor,
    ConductorVehiculo,
    MaterialConstruccion,
    MetodoPago,
    Notificacion,
    Proveedor,
    Stock,
    UnidadMedida,
    Usuario,
    Vehiculo,
)


class UsuarioAdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = (
            "username",
            "email",
            "nombres",
            "apellidos",
            "telefono",
            "documento",
            "tipo_documento",
            "rol",
            "estado",
        )


class UsuarioAdminChangeForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = "__all__"


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    add_form = UsuarioAdminCreationForm
    form = UsuarioAdminChangeForm
    model = Usuario

    list_display = (
        "username",
        "nombres",
        "apellidos",
        "email",
        "documento",
        "rol",
        "estado",
        "is_staff",
    )
    list_filter = ("rol", "estado", "tipo_documento", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "nombres", "apellidos", "email", "documento")
    ordering = ("username",)
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Información personal",
            {
                "fields": (
                    "nombres",
                    "apellidos",
                    "email",
                    "telefono",
                    "documento",
                    "tipo_documento",
                    "foto_perfil",
                )
            },
        ),
        ("Rol y estado", {"fields": ("rol", "estado", "sincronizado")}),
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Fechas importantes", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "nombres",
                    "apellidos",
                    "telefono",
                    "documento",
                    "tipo_documento",
                    "rol",
                    "estado",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "abreviatura", "activa", "orden")
    list_filter = ("activa",)
    search_fields = ("codigo", "nombre", "abreviatura")
    ordering = ("orden", "nombre")
    readonly_fields = ("fecha_creacion",)

    fieldsets = (
        ("Información básica", {"fields": ("codigo", "nombre", "abreviatura", "descripcion")}),
        (
            "Control",
            {
                "fields": ("activa", "orden", "fecha_creacion"),
                "classes": ("collapse",),
            },
        ),
    )


admin.site.register(EPS)
admin.site.register(Conductor)
admin.site.register(Vehiculo)
admin.site.register(ConductorVehiculo)
admin.site.register(Catalogo)
admin.site.register(Proveedor)
admin.site.register(MaterialConstruccion)
admin.site.register(Stock)
admin.site.register(MetodoPago)
admin.site.register(Notificacion)
