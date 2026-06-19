"""
Vistas de Inventario, separadas por dominio.
"""
from .materiales_views import (
    materiales_lista, crear_material, editar_material, eliminar_material,
    stock_lista, editar_stock, buscar_materiales
)
from .movimientos_views import registrar_entrada, movimientos_lista
from .catalogo_views import (
    tipos_material_lista, crear_tipo_material, editar_tipo_material,
    eliminar_tipo_material
)
from .api_views import api_materiales

__all__ = [
    'materiales_lista', 'crear_material', 'editar_material', 'eliminar_material',
    'stock_lista', 'editar_stock', 'buscar_materiales',
    'registrar_entrada', 'movimientos_lista',
    'tipos_material_lista', 'crear_tipo_material', 'editar_tipo_material',
    'eliminar_tipo_material',
    'api_materiales',
]
