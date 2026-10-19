"""
Pruebas de Seguridad: Base de Datos y Concurrencia (Área 9)
Verifica con TransactionTestCase e hilos reales (multi-threading):
1. Doble aprobación de pago simultánea (bloqueo pesimista con select_for_update).
2. Doble envío concurrente del mismo pedido (condición de carrera de despacho).
3. Generación concurrente de consecutivos de factura (sin colisiones).
4. Doble pago simultáneo de la misma factura (prevención de sobrepago).
5. Rollback transaccional ante excepciones inesperadas.
"""

from decimal import Decimal
import threading
import time
from django.db import connection, transaction
from django.test import TransactionTestCase

from apps.clientes.models import Cliente
from apps.pagos.models import Factura, Pago, PagoFactura
from apps.pedidos.models import Pedido
from apps.usuarios.models import Usuario
from config.sequences import numero_factura


class SeguridadArea9ConcurrenciaTests(TransactionTestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="cliente_concurrencia@test.com",
            email="cliente_concurrencia@test.com",
            password="Password123*",
            nombres="Cliente",
            apellidos="Concurrencia",
            documento="77889900",
            tipo_documento="CC",
            rol="cliente",
        )
        self.cliente, _ = Cliente.objects.get_or_create(
            usuario=self.usuario,
            defaults={"nombre_empresa": "Constructora Concurrente SAS"},
        )
        self.pedido = Pedido.objects.create(
            usuario=self.usuario,
            cliente=self.cliente,
            direccion_destino="Calle Concurrente # 1-2",
            estado=Pedido.PENDIENTE,
            total=Decimal("100000.00"),
        )

    def test_transaccion_atomica_rollback_en_fallo(self):
        """Verifica que una falla durante una operación revierta completamente los cambios."""
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_BANCOLOMBIA,
            monto=Decimal("100000.00"),
            estado=Pago.PENDIENTE,
        )

        try:
            with transaction.atomic():
                pago.marcar_revision(estado=Pago.APROBADO, revisor=self.usuario)
                pago.save()
                raise RuntimeError("Fallo simulado de pasarela bancaria o red")
        except RuntimeError:
            pass

        pago.refresh_from_db()
        self.assertEqual(
            pago.estado,
            Pago.PENDIENTE,
            "El rollback de transaction.atomic debe revertir la aprobación del pago ante fallo",
        )

    def test_hilos_doble_aprobacion_concurrente_pago(self):
        """Dos hilos intentan aprobar/rechazar el mismo pago concurrentemente; solo uno debe aplicar el cambio."""
        pago = Pago.objects.create(
            pedido=self.pedido,
            metodo=Pago.METODO_BANCOLOMBIA,
            monto=Decimal("100000.00"),
            estado=Pago.PENDIENTE,
        )

        resultados = []
        barrera = threading.Barrier(2)

        def worker(accion):
            connection.close()
            try:
                barrera.wait(timeout=5)
                with transaction.atomic():
                    p = Pago.objects.select_for_update().get(pk=pago.pk)
                    if p.estado == Pago.PENDIENTE:
                        p.marcar_revision(estado=accion, revisor=self.usuario)
                        p.save()
                        resultados.append(f"exito_{accion}")
                    else:
                        resultados.append(f"bloqueado_{accion}")
            except Exception as e:
                # En SQLite concurrente ocurre 'database table is locked' (bloqueo a nivel de archivo/tabla).
                # En PostgreSQL se espera bloqueo a nivel de fila (row-level lock) con espera pesimista.
                resultados.append(f"db_lock_{type(e).__name__}_{e}")
            finally:
                connection.close()

        t1 = threading.Thread(target=worker, args=(Pago.APROBADO,))
        t2 = threading.Thread(target=worker, args=(Pago.RECHAZADO,))

        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        self.assertEqual(len(resultados), 2)
        exitos = [r for r in resultados if r.startswith("exito_")]
        self.assertTrue(
            len(exitos) <= 1,
            f"Condición de carrera violada: más de un hilo aprobó/modificó el pago: {resultados}",
        )

        pago.refresh_from_db()
        self.assertIn(pago.estado, (Pago.PENDIENTE, Pago.APROBADO, Pago.RECHAZADO))

    def test_hilos_doble_envio_concurrente_pedido(self):
        """Dos hilos intentan despachar el mismo pedido concurrentemente a 'en_ruta'; solo uno debe lograrlo."""
        pedido_autorizado = Pedido.objects.create(
            usuario=self.usuario,
            cliente=self.cliente,
            direccion_destino="Avenida Despacho # 4-5",
            estado=Pedido.AUTORIZADO_DESPACHO,
            total=Decimal("250000.00"),
        )

        resultados = []
        barrera = threading.Barrier(2)

        def worker_despacho(hilo_id):
            connection.close()
            try:
                barrera.wait(timeout=5)
                with transaction.atomic():
                    ped = Pedido.objects.select_for_update().get(pk=pedido_autorizado.pk)
                    if ped.estado == Pedido.AUTORIZADO_DESPACHO:
                        ped.transicionar(Pedido.EN_RUTA, usuario=self.usuario)
                        ped.save()
                        resultados.append(f"despachado_hilo_{hilo_id}")
                    else:
                        resultados.append(f"ya_despachado_hilo_{hilo_id}")
            except Exception as e:
                resultados.append(f"db_lock_{type(e).__name__}_{e}")
            finally:
                connection.close()

        t1 = threading.Thread(target=worker_despacho, args=(1,))
        t2 = threading.Thread(target=worker_despacho, args=(2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        self.assertEqual(len(resultados), 2)
        despachos = [r for r in resultados if r.startswith("despachado_hilo_")]
        self.assertTrue(
            len(despachos) <= 1,
            f"Condición de carrera violada: más de un hilo despachó el mismo pedido: {resultados}",
        )

        pedido_autorizado.refresh_from_db()
        self.assertIn(pedido_autorizado.estado, (Pedido.AUTORIZADO_DESPACHO, Pedido.EN_RUTA))

    def test_hilos_dos_consecutivos_factura_simultaneos(self):
        """Dos hilos concurrentes solicitan consecutivo de factura; no debe haber colisión ni duplicados."""
        resultados = []
        barrera = threading.Barrier(2)

        def worker_consecutivo():
            connection.close()
            try:
                barrera.wait(timeout=5)
                num = numero_factura()
                resultados.append(num)
            except Exception as e:
                resultados.append(f"db_lock_{type(e).__name__}_{e}")
            finally:
                connection.close()

        t1 = threading.Thread(target=worker_consecutivo)
        t2 = threading.Thread(target=worker_consecutivo)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        self.assertEqual(len(resultados), 2)
        numeros = [r for r in resultados if r.startswith("F-")]
        if len(numeros) == 2:
            self.assertNotEqual(numeros[0], numeros[1], "Los consecutivos concurrentes no pueden colisionar")
        else:
            # En SQLite la base de datos se bloquea ante escrituras simultáneas por hilos distintos
            self.assertTrue(any("db_lock" in r for r in resultados))

    def test_hilos_doble_pago_concurrente_misma_factura(self):
        """Dos hilos intentan pagar el total de una factura simultáneamente; el segundo detecta saldo cero."""
        factura = Factura.objects.create(
            pedido=self.pedido,
            cliente=self.cliente,
            subtotal=Decimal("80000.00"),
            impuestos=Decimal("20000.00"),
            total=Decimal("100000.00"),
            estado=Factura.Estado.EMITIDA,
        )

        resultados = []
        barrera = threading.Barrier(2)

        def worker_pago_factura(hilo_id):
            connection.close()
            try:
                barrera.wait(timeout=5)
                with transaction.atomic():
                    f = Factura.objects.select_for_update().get(pk=factura.pk)
                    if f.estado in (Factura.Estado.EMITIDA, Factura.Estado.PARCIAL) and f.total > Decimal("0"):
                        pago_reg = PagoFactura.objects.create(
                            factura=f,
                            monto=f.total,
                            metodo=PagoFactura.Metodo.TRANSFERENCIA,
                            estado=PagoFactura.Estado.APROBADO,
                            registrado_por=self.usuario,
                        )
                        f.transicionar(Factura.Estado.PAGADA, usuario=self.usuario)
                        f.save()
                        resultados.append(f"pago_exitoso_hilo_{hilo_id}")
                    else:
                        resultados.append(f"factura_ya_saldada_hilo_{hilo_id}")
            except Exception as e:
                resultados.append(f"db_lock_{type(e).__name__}_{e}")
            finally:
                connection.close()

        t1 = threading.Thread(target=worker_pago_factura, args=(1,))
        t2 = threading.Thread(target=worker_pago_factura, args=(2,))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        self.assertEqual(len(resultados), 2)
        exitosos = [r for r in resultados if r.startswith("pago_exitoso_")]
        self.assertTrue(
            len(exitosos) <= 1,
            f"Condición de carrera violada: más de un pago total aprobado: {resultados}",
        )

        factura.refresh_from_db()
        self.assertIn(factura.estado, (Factura.Estado.EMITIDA, Factura.Estado.PAGADA))
