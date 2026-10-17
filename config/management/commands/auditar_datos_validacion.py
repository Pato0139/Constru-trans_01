"""Comando de auditoría de datos para validar integridad previa a migraciones de restricciones."""

from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Audita la base de datos en busca de registros que violen las nuevas restricciones de validación."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Iniciando auditoría de datos de validación..."))

        hallazgos = 0

        consultas = [
            (
                "Pedidos con montos o porcentajes negativos / fuera de rango",
                """
                SELECT codigo_pedido, subtotal, impuesto, descuento, impuesto_porcentaje
                FROM pedido
                WHERE subtotal < 0 OR impuesto < 0 OR descuento < 0
                   OR impuesto_porcentaje < 0 OR impuesto_porcentaje > 100;
                """,
            ),
            (
                "Pedidos con fecha de entrega real anterior a la toma de entrega",
                """
                SELECT codigo_pedido, fecha_toma_entrega, fecha_entrega_real
                FROM pedido
                WHERE fecha_toma_entrega IS NOT NULL
                  AND fecha_entrega_real IS NOT NULL
                  AND fecha_entrega_real < fecha_toma_entrega;
                """,
            ),
            (
                "Facturas con total negativo",
                """
                SELECT id_factura, numero, total
                FROM factura
                WHERE total < 0;
                """,
            ),
            (
                "Pagos de factura con monto menor o igual a cero",
                """
                SELECT id, factura_id, monto
                FROM pago_factura
                WHERE monto <= 0;
                """,
            ),
            (
                "Detalles de pago con monto menor o igual a cero",
                """
                SELECT id, monto
                FROM detalle_pago
                WHERE monto <= 0;
                """,
            ),
            (
                "Compras con subtotales o impuestos inválidos",
                """
                SELECT id_compra, subtotal, impuesto, total_compra, impuesto_porcentaje
                FROM compra
                WHERE subtotal < 0 OR impuesto < 0 OR total_compra < 0
                   OR impuesto_porcentaje < 0 OR impuesto_porcentaje > 100;
                """,
            ),
            (
                "Detalles de compra con cantidad o precio <= 0",
                """
                SELECT id_detalle_compra, id_compra, cantidad, precio_unitario
                FROM detalle_compra
                WHERE cantidad <= 0 OR precio_unitario <= 0;
                """,
            ),
            (
                "Clientes con gasto acumulado negativo",
                """
                SELECT usuario_id, gasto_acumulado
                FROM cliente_vip
                WHERE gasto_acumulado < 0;
                """,
            ),
            (
                "Facturas con números duplicados",
                """
                SELECT numero, COUNT(*) as cantidad
                FROM factura
                GROUP BY numero
                HAVING COUNT(*) > 1;
                """,
            ),
        ]

        tablas_existentes = {t.lower() for t in connection.introspection.table_names()}

        with connection.cursor() as cursor:
            for titulo, query in consultas:
                # Comprobar si la tabla involucrada existe
                tabla_en_query = None
                for t in ["pedido", "factura", "pago_factura", "detalle_pago", "compra", "detalle_compra", "cliente_vip"]:
                    if f"from {t}" in query.lower():
                        tabla_en_query = t
                        break

                if tabla_en_query and tabla_en_query not in tablas_existentes:
                    self.stdout.write(self.style.WARNING(f"[-] Saltando '{titulo}': tabla '{tabla_en_query}' no existe."))
                    continue

                try:
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    if rows:
                        hallazgos += len(rows)
                        self.stdout.write(self.style.ERROR(f"[!] {titulo}: {len(rows)} registro(s) encontrado(s):"))
                        for row in rows[:5]:
                            self.stdout.write(f"    -> {row}")
                        if len(rows) > 5:
                            self.stdout.write(f"    ... y {len(rows) - 5} más.")
                    else:
                        self.stdout.write(self.style.SUCCESS(f"[OK] {titulo}: 0 anomalías."))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"[?] Error al ejecutar auditoría para '{titulo}': {e}"))

        if hallazgos == 0:
            self.stdout.write(self.style.SUCCESS("\nAuditoría completada sin anomalías. La base de datos es apta para aplicar migraciones con CheckConstraints."))
        else:
            self.stdout.write(self.style.ERROR(f"\nSe encontraron {hallazgos} anomalía(s) que deben corregirse antes de migrar las restricciones de base de datos."))
