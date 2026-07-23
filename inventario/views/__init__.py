"""
Vistas de Inventario, separadas por dominio.
"""

from .api_views import api_materiales, api_materiales_listado
from .catalogo_views import (
    crear_tipo_material,
    crear_unidad_medida,
    cambiar_estado_unidad_medida,
    editar_tipo_material,
    editar_unidad_medida,
    eliminar_tipo_material,
    eliminar_unidad_medida,
    tipos_material_lista,
    unidades_medida_lista,
)
from .materiales_views import (
    buscar_materiales,
    cambiar_estado_material,
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
    "cambiar_estado_material",
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
    "unidades_medida_lista",
    "cambiar_estado_unidad_medida",
    "crear_unidad_medida",
    "editar_unidad_medida",
    "eliminar_unidad_medida",
    "api_materiales",
    "api_materiales_listado",
]
