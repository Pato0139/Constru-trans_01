from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.usuarios.models import Usuario, Material
from .models import Orden, DetalleOrden
import json


class AgregarMaterialPedidoTests(TestCase):

    def setUp(self):
        self.client = Client()
        auth_user = User.objects.create_user(username="cliente1", password="pass123")
        self.usuario = Usuario.objects.create(
            user=auth_user, rol="cliente",
            nombres="Ana", apellidos="López",
            tipo_documento="CC", documento="123456"
        )
        self.client.login(username="cliente1", password="pass123")

        self.material = Material.objects.create(
            nombre="Cemento", tipo="Cemento",
            descripcion="Cemento gris", precio=25000, stock=50
        )
        self.material_sin_stock = Material.objects.create(
            nombre="Arena", tipo="Arena",
            descripcion="Arena fina", precio=10000, stock=0
        )
        self.orden_pendiente = Orden.objects.create(
            cliente=self.usuario,
            direccion_origen="Calle 1",
            direccion_destino="Calle 2",
            estado=Orden.PENDIENTE
        )
        self.orden_en_ruta = Orden.objects.create(
            cliente=self.usuario,
            direccion_origen="Calle 3",
            direccion_destino="Calle 4",
            estado=Orden.EN_RUTA
        )

    def test_pedido_no_pendiente_retorna_400(self):
        response = self.client.post(
            f'/ordenes/{self.orden_en_ruta.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 2}
        )
        self.assertEqual(response.status_code, 400)

    def test_material_sin_stock_retorna_400(self):
        response = self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material_sin_stock.id, "cantidad": 1}
        )
        self.assertEqual(response.status_code, 400)

    def test_cantidad_supera_stock_retorna_400(self):
        response = self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 999}
        )
        self.assertEqual(response.status_code, 400)

    def test_agregar_material_exitoso(self):
        response = self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 5}
        )
        self.assertEqual(response.status_code, 302)

    def test_total_se_actualiza_automaticamente(self):
        self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 2}
        )
        self.orden_pendiente.refresh_from_db()
        esperado = 2 * self.material.precio
        self.assertEqual(self.orden_pendiente.precio, esperado)

    def test_cantidad_cero_retorna_400(self):
        response = self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 0}
        )
        self.assertEqual(response.status_code, 400)


class EliminarMaterialPedidoTests(TestCase):

    def setUp(self):
        self.client = Client()
        auth_user = User.objects.create_user(username="cliente2", password="pass123")
        self.usuario = Usuario.objects.create(
            user=auth_user, rol="cliente",
            nombres="Pedro", apellidos="Gómez",
            tipo_documento="CC", documento="654321"
        )
        self.client.login(username="cliente2", password="pass123")

        self.material = Material.objects.create(
            nombre="Grava", tipo="Grava",
            descripcion="Grava fina", precio=15000, stock=30
        )
        self.orden_pendiente = Orden.objects.create(
            cliente=self.usuario,
            direccion_origen="Calle 5",
            direccion_destino="Calle 6",
            estado=Orden.PENDIENTE
        )
        self.orden_en_ruta = Orden.objects.create(
            cliente=self.usuario,
            direccion_origen="Calle 7",
            direccion_destino="Calle 8",
            estado=Orden.EN_RUTA
        )
        self.detalle = DetalleOrden.objects.create(
            orden=self.orden_pendiente,
            material=self.material,
            cantidad=3,
            precio_unitario=self.material.precio
        )

    def test_no_eliminar_si_no_pendiente(self):
        detalle_en_ruta = DetalleOrden.objects.create(
            orden=self.orden_en_ruta,
            material=self.material,
            cantidad=2,
            precio_unitario=self.material.precio
        )
        response = self.client.get(
            f'/ordenes/{self.orden_en_ruta.id}/materiales/{detalle_en_ruta.id}/eliminar/'
        )
        self.assertEqual(response.status_code, 400)

    def test_eliminar_material_exitoso(self):
        response = self.client.get(
            f'/ordenes/{self.orden_pendiente.id}/materiales/{self.detalle.id}/eliminar/'
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DetalleOrden.objects.filter(id=self.detalle.id).exists())

    def test_total_se_recalcula_al_eliminar(self):
        self.client.get(
            f'/ordenes/{self.orden_pendiente.id}/materiales/{self.detalle.id}/eliminar/'
        )
        self.orden_pendiente.refresh_from_db()
        self.assertEqual(self.orden_pendiente.precio, 0)

    def test_detalle_de_otra_orden_retorna_404(self):
        otra_orden = Orden.objects.create(
            cliente=self.usuario,
            direccion_origen="Calle 9",
            direccion_destino="Calle 10",
            estado=Orden.PENDIENTE
        )
        response = self.client.get(
            f'/ordenes/{otra_orden.id}/materiales/{self.detalle.id}/eliminar/'
        )
        self.assertEqual(response.status_code, 404)