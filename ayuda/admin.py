from django.contrib import admin
from .models import (
    CategoriaAyuda,
    GuiaEdicion,
    PasoGuia,
    SugerenciaRecomendacion,
    ManualUsuario,
    ColorSistema,
)


@admin.register(CategoriaAyuda)
class CategoriaAyudaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "orden"]
    list_editable = ["orden"]
    search_fields = ["nombre"]


class PasoGuiaInline(admin.TabularInline):
    model = PasoGuia
    extra = 1


@admin.register(GuiaEdicion)
class GuiaEdicionAdmin(admin.ModelAdmin):
    list_display = ["titulo", "categoria", "orden", "activo", "es_favorito"]
    list_filter = ["categoria", "activo", "es_favorito"]
    list_editable = ["orden", "activo", "es_favorito"]
    search_fields = ["titulo", "contenido"]
    inlines = [PasoGuiaInline]


@admin.register(SugerenciaRecomendacion)
class SugerenciaRecomendacionAdmin(admin.ModelAdmin):
    list_display = ["titulo", "usuario", "tipo", "estado", "fecha_creacion"]
    list_filter = ["tipo", "estado", "fecha_creacion"]
    list_editable = ["estado"]
    search_fields = ["titulo", "descripcion"]
    date_hierarchy = "fecha_creacion"


@admin.register(ManualUsuario)
class ManualUsuarioAdmin(admin.ModelAdmin):
    list_display = ["titulo", "version", "fecha_publicacion", "activo"]
    list_filter = ["activo", "fecha_publicacion"]
    list_editable = ["activo"]
    search_fields = ["titulo"]


@admin.register(ColorSistema)
class ColorSistemaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo_hex", "uso", "activo"]
    list_filter = ["activo"]
    list_editable = ["activo"]
    search_fields = ["nombre", "descripcion", "uso"]
