from django.contrib import admin

from .models import (
    CategoriaAyuda,
    ColorSistema,
    GuiaEdicion,
    ManualUsuario,
    PasoGuia,
    SugerenciaRecomendacion,
)


@admin.register(CategoriaAyuda)
class CategoriaAyudaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "orden"]
    list_editable = ["orden"]
    search_fields = ["nombre", "descripcion"]


class PasoGuiaInline(admin.TabularInline):
    model = PasoGuia
    extra = 1


@admin.register(GuiaEdicion)
class GuiaEdicionAdmin(admin.ModelAdmin):
    list_display = ["titulo", "categoria", "orden", "activo", "es_favorito", "fecha_creacion"]
    list_filter = ["categoria", "activo", "es_favorito", "fecha_creacion"]
    list_editable = ["orden", "activo", "es_favorito"]
    search_fields = ["titulo", "contenido", "categoria__nombre"]
    list_select_related = ["categoria"]
    inlines = [PasoGuiaInline]


@admin.register(SugerenciaRecomendacion)
class SugerenciaRecomendacionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "usuario", "tipo", "estado", "fecha_creacion", "fecha_actualizacion")
    list_filter = ("tipo", "estado", "fecha_creacion", "usuario")
    list_editable = ("estado",)
    search_fields = ("titulo", "descripcion", "usuario__nombres", "usuario__apellidos")
    list_select_related = ("usuario",)
    date_hierarchy = "fecha_creacion"


@admin.register(ManualUsuario)
class ManualUsuarioAdmin(admin.ModelAdmin):
    list_display = ["titulo", "version", "fecha_publicacion", "activo"]
    list_filter = ["activo", "fecha_publicacion"]
    list_editable = ["activo"]
    search_fields = ["titulo", "version"]


@admin.register(ColorSistema)
class ColorSistemaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo_hex", "uso", "activo"]
    list_filter = ["activo"]
    list_editable = ["activo"]
    search_fields = ["nombre", "descripcion", "uso"]
