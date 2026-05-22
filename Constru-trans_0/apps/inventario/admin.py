from django.contrib import admin
from .models import MovimientoInventario


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('id_movimiento', 'material', 'tipo_movimiento', 'cantidad', 'fecha', 'usuario')
    list_filter = ('tipo_movimiento', 'fecha', 'material')
    search_fields = ('material__nombre', 'observacion')
    readonly_fields = ('fecha',)
