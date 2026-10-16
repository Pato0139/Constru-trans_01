"""Re-exporta clases de config.forms_base para comodidad de importación."""

from config.forms_base import (
    CAMPOS_SISTEMA,
    StrictForm,
    StrictFormMixin,
    StrictModelForm,
)

__all__ = ["CAMPOS_SISTEMA", "StrictForm", "StrictFormMixin", "StrictModelForm"]
