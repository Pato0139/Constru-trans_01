"""
Vistas de Inventario, separadas por dominio.
"""

from .api_views import api_materiales, api_materiales_listado
from .catalogo_views import (
    crear_tipo_material,
    editar_tipo_material,
    eliminar_tipo_material,
    tipos_material_lista,
)
from .materiales_views import (
    buscar_materiales,
    crear_material,
    editar_material,
    editar_stock,
    eliminar_material,
    materiales_lista,
    stock_lista,
)
from .movimientos_views import movimientos_lista, registrar_entrada

__all__ = [
    "materiales_lista",
    "crear_material",
    "editar_material",
    "eliminar_material",
    "stock_lista",
    "editar_stock",
    "buscar_materiales",
    "registrar_entrada",
    "movimientos_lista",
    "tipos_material_lista",
    "crear_tipo_material",
    "editar_tipo_material",
    "eliminar_tipo_material",
    "api_materiales",
    "api_materiales_listado",
]
