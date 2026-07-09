"""
Servicios de dominio para Inventario.

Encapsula toda la lógica de negocio (Kardex, stock, alertas).
Los views NO escriben querysets directos — delegan a estos servicios.
"""

from .kardex import KardexService, ResumenKardex, StockService

__all__ = ["KardexService", "StockService", "ResumenKardex"]
