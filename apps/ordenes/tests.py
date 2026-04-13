from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.usuarios.models import Usuario, Material
from .models import Orden
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
            nombre="Cemento", tipo="construccion",
            descripcion="Cemento gris", precio=25000, stock=50
        )
        self.material_sin_stock = Material.objects.create(
            nombre="Arena", tipo="construccion",
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

    # CT-293 — Pedido no pendiente debe retornar 400
    def test_pedido_no_pendiente_retorna_400(self):
        response = self.client.post(
            f'/ordenes/{self.orden_en_ruta.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 2}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("pendiente", data["error"])

    # CT-294 — Material sin stock debe retornar 400
    def test_material_sin_stock_retorna_400(self):
        response = self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material_sin_stock.id, "cantidad": 1}
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn("stock", data["error"])

    # CT-294 — Cantidad mayor al stock disponible retorna 400
    def test_cantidad_supera_stock_retorna_400(self):
        response = self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 999}
        )
        self.assertEqual(response.status_code, 400)

    # CT-296 — Agregar material exitosamente retorna 201
    def test_agregar_material_exitoso(self):
        response = self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 5}
        )
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data["detalle"]["material"], "Cemento")
        self.assertEqual(data["detalle"]["cantidad"], 5)

    # CT-295 — El total se actualiza automáticamente
    def test_total_se_actualiza_automaticamente(self):
        self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 2}
        )
        self.orden_pendiente.refresh_from_db()
        esperado = 2 * self.material.precio
        self.assertEqual(self.orden_pendiente.precio, esperado)

    # Cantidad = 0 retorna 400
    def test_cantidad_cero_retorna_400(self):
        response = self.client.post(
            f'/ordenes/{self.orden_pendiente.id}/materiales/',
            {"material_id": self.material.id, "cantidad": 0}
        )
        self.assertEqual(response.status_code, 400)