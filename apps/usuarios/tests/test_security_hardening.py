from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import Catalogo, Marca, MaterialConstruccion, Stock, UnidadMedida
from apps.usuarios.models import Usuario


class SecurityHardeningTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username="sec_admin",
            email="sec_admin@test.com",
            password="StrongPass#2026!",
            nombres="Admin",
            apellidos="Seguridad",
            documento="1111111111",
            tipo_documento="CC",
            telefono="3001111111",
            rol="admin",
        )
        self.cliente = Usuario.objects.create_user(
            username="sec_cliente",
            email="sec_cliente@test.com",
            password="StrongPass#2026!",
            nombres="Cliente",
            apellidos="Prueba",
            documento="2222222222",
            tipo_documento="CC",
            telefono="3002222222",
            rol="cliente",
        )
        self.conductor = Usuario.objects.create_user(
            username="sec_conductor",
            email="sec_conductor@test.com",
            password="StrongPass#2026!",
            nombres="Conductor",
            apellidos="Prueba",
            documento="3333333333",
            tipo_documento="CC",
            telefono="3003333333",
            rol="conductor",
        )
        cat = Catalogo.objects.create(codigo_catalogo="SEC01", nombre_empresa="Cementos")
        unidad = UnidadMedida.objects.create(codigo="UND", nombre="Unidad", abreviatura="und")
        marca = Marca.objects.create(nombre="MarcaSec")
        self.material = MaterialConstruccion.objects.create(
            nombre="Cemento Seguro",
            catalogo=cat,
            unidad_medida=unidad,
            marca=marca,
            precio_referencia=Decimal("30000.00"),
            activo=True,
            estado="activo",
        )
        self.stock = Stock.objects.create(
            material=self.material, cantidad_actual=20, stock_minimo=5, ubicacion="Bodega 1"
        )

    def test_cliente_bloqueado_en_rutas_admin(self):
        self.client.force_login(self.cliente)
        for url_name in (
            "auditoria:lista_historial",
            "usuarios:lista_usuarios",
            "compras:lista_compras",
            "logistica:lista_vehiculos",
        ):
            resp = self.client.get(reverse(url_name))
            self.assertEqual(resp.status_code, 403, f"Cliente pudo acceder a {url_name}")

    def test_conductor_bloqueado_en_rutas_admin(self):
        self.client.force_login(self.conductor)
        for url_name in ("usuarios:lista_usuarios", "compras:lista_compras"):
            resp = self.client.get(reverse(url_name))
            self.assertEqual(resp.status_code, 403, f"Conductor pudo acceder a {url_name}")

    def test_open_redirect_bloqueado_en_cambiar_contrasena(self):
        self.client.force_login(self.cliente)
        resp = self.client.post(
            reverse("usuarios:cambiar_password_perfil"),
            {"old_password": "wrong", "new_password1": "NewPass#2026!", "new_password2": "NewPass#2026!"},
            HTTP_REFERER="https://evil.example/phish",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(resp["Location"].startswith("https://evil.example"))

    def test_cliente_no_puede_escalar_privilegios_en_editar_perfil(self):
        self.client.force_login(self.cliente)
        self.client.post(
            reverse("usuarios:editar_perfil"),
            {
                "nombres": "Cliente",
                "apellidos": "Hack",
                "email": self.cliente.email,
                "telefono": "3002222222",
                "rol": "admin",
                "is_superuser": "true",
                "is_staff": "true",
            },
        )
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.rol, "cliente")
        self.assertFalse(self.cliente.is_superuser)

    def test_stock_rechaza_cantidades_negativas_desde_devtools(self):
        self.client.force_login(self.admin)
        self.client.post(
            reverse("catalogo:editar_stock", args=[self.material.pk]),
            {"cantidad": "-50", "stock_minimo": "-5", "ubicacion": "Bodega 1"},
        )
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.cantidad_actual, 20)
        self.assertEqual(self.stock.stock_minimo, 5)

    def test_soft_delete_no_borra_material_ni_usuario(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("catalogo:eliminar_material", args=[self.material.pk]))
        self.material.refresh_from_db()
        self.assertFalse(self.material.activo)
        self.assertEqual(self.material.estado, "inactivo")

        self.client.post(reverse("usuarios:eliminar_usuario", args=[self.cliente.pk]))
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.is_active)
        self.assertEqual(self.cliente.estado, "inactivo")
