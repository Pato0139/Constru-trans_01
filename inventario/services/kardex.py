"""
Kardex — registro de entradas/salidas y cálculo de stock.

Patrón combinado de:
- mine-inventory/inventario/models.py → MovimientoInventario con tipo/cantidad/fecha
- proyecto-licorera/inventario/models.py → tipos entrada/salida/ajuste + Lote

IMPORTANTE: Usa tu router `debe_usar_bd_remota()` para mantener
el modo offline-first.
"""

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.db.models import F, Sum

from core.db_preference import debe_usar_bd_remota
from usuarios.models import MaterialConstruccion as Material
from usuarios.models import Stock

from ..models import MovimientoInventario


@dataclass
class ResumenKardex:
    """Resumen del Kardex de un material en un período."""

    material_id: int
    entradas: int
    salidas: int
    ajustes: int
    saldo_actual: int
    periodo_inicio: datetime
    periodo_fin: datetime


class KardexService:
    """Servicio para gestionar movimientos de inventario."""

    @staticmethod
    def get_db_alias():
        return "remota" if debe_usar_bd_remota() else "default"

    @classmethod
    def registrar_movimiento(
        cls,
        *,
        material_id: int,
        tipo: str,
        cantidad: int,
        observacion: str = "",
        usuario=None,
        compra_id: int | None = None,
        pedido_id: int | None = None,
    ) -> MovimientoInventario:
        if tipo not in ("entrada", "salida", "ajuste"):
            raise ValueError(f"Tipo inválido: {tipo}. Use 'entrada'|'salida'|'ajuste'.")
        if cantidad <= 0:
            raise ValueError("Cantidad debe ser mayor a 0.")

        db_alias = cls.get_db_alias()

        with transaction.atomic(using=db_alias):
            material = Material.objects.select_for_update().using(db_alias).get(pk=material_id)
            stock, _ = (
                Stock.objects.select_for_update()
                .using(db_alias)
                .get_or_create(material=material, defaults={"cantidad_actual": 0})
            )

            if tipo == "entrada":
                stock.cantidad_actual = F("cantidad_actual") + cantidad
            elif tipo == "salida":
                if stock.cantidad_actual < cantidad:
                    raise ValueError(
                        f"Stock insuficiente para {material.nombre}: "
                        f"disponible={stock.cantidad_actual}, requerido={cantidad}"
                    )
                stock.cantidad_actual = F("cantidad_actual") - cantidad
            else:  # ajuste
                stock.cantidad_actual = cantidad

            stock.save(using=db_alias)
            stock.refresh_from_db(using=db_alias)

            # Para 'ajuste' guardamos como 'entrada' para mantener choices del modelo.
            tipo_a_guardar = "entrada" if tipo == "ajuste" else tipo

            return MovimientoInventario.objects.using(db_alias).create(
                material=material,
                tipo_movimiento=tipo_a_guardar,
                cantidad=cantidad,
                observacion=observacion,
                usuario=usuario,
                compra_id=compra_id,
                pedido_id=pedido_id,
            )

    @classmethod
    def resumen_periodo(
        cls, material_id: int, fecha_inicio: datetime, fecha_fin: datetime
    ) -> ResumenKardex:
        qs = MovimientoInventario.objects.filter(
            material_id=material_id,
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
        )
        entradas = qs.filter(tipo_movimiento="entrada").aggregate(t=Sum("cantidad"))["t"] or 0
        salidas = qs.filter(tipo_movimiento="salida").aggregate(t=Sum("cantidad"))["t"] or 0
        try:
            saldo = Stock.objects.get(material_id=material_id).cantidad_actual
        except Stock.DoesNotExist:
            saldo = 0

        return ResumenKardex(
            material_id=material_id,
            entradas=entradas,
            salidas=salidas,
            ajustes=0,
            saldo_actual=saldo,
            periodo_inicio=fecha_inicio,
            periodo_fin=fecha_fin,
        )

    @classmethod
    def alertas_stock_bajo(cls, umbral: int = 10):
        """Materiales con stock <= umbral (de mine-inventory)."""
        return (
            Stock.objects.select_related("material")
            .filter(cantidad_actual__lte=umbral)
            .order_by("cantidad_actual")
        )


class StockService:
    """Consultas de stock: cálculo, sincronización y auditoría."""

    @staticmethod
    def stock_actual(material_id: int) -> int:
        try:
            return Stock.objects.get(material_id=material_id).cantidad_actual
        except Stock.DoesNotExist:
            return 0

    @staticmethod
    def materiales_sin_stock() -> list:
        return list(Material.objects.filter(stock__cantidad_actual__lte=0).select_related("stock"))
