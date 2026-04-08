from django.contrib import admin
from .models import Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'tipo', 'precio', 'stock', 'activo']
    list_filter = ['tipo', 'activo']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activo']