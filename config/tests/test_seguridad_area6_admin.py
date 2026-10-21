"""
Pruebas de Seguridad: Panel de Administración de Django (Área 6)
Verifica:
1. Restricción de acceso a Django admin: requiere is_staff=True Y rol='admin' (o superuser).
2. Restricción de borrado en modelos críticos (Pedido, Pago, Factura): has_delete_permission es False para staff regular.
3. Optimización contra N+1 queries (list_select_related) en list_display de admin.
"""

from decimal import Decimal
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.pagos.models import Factura, Pago
from apps.pedidos.models import Pedido

User = get_user_model()


class SeguridadArea6AdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # Usuario staff con rol conductor (NO debe entrar al admin)
        self.staff_conductor = User.objects.create_user(
            username="staff_conductor@test.com",
            email="staff_conductor@test.com",
            password="Password123*",
            nombres="Staff",
            apellidos="Conductor",
            documento="11223344",
            tipo_documento="CC",
            rol="conductor",
            is_staff=True,
        )
        # Usuario admin regular (con is_staff=True y rol='admin')
        self.admin_staff = User.objects.create_user(
            username="admin_regular@test.com",
            email="admin_regular@test.com",
            password="Password123*",
            nombres="Admin",
            apellidos="Regular",
            documento="22334455",
            tipo_documento="CC",
            rol="admin",
            is_staff=True,
        )
        # Superusuario global legítimo
        self.superuser = User.objects.create_superuser(
            username="Edward_Fonseca",
            email="edwardf5432@gmail.com",
            password="Password123*",
            nombres="Edward",
            apellidos="Fonseca",
            documento="33445566",
            tipo_documento="CC",
            rol="admin",
        )

    def test_staff_con_rol_distinto_de_admin_no_tiene_permiso_en_admin_site(self):
        """Un usuario con is_staff=True pero rol conductor o cliente no debe acceder al admin."""
        request = self.factory.get("/admin/")
        request.user = self.staff_conductor
        self.assertFalse(
            admin.site.has_permission(request),
            "is_staff sin rol='admin' no debe tener permiso en admin.site",
        )

    def test_admin_staff_tiene_permiso_en_admin_site(self):
        """Un usuario con is_staff=True y rol='admin' sí puede acceder al admin."""
        request = self.factory.get("/admin/")
        request.user = self.admin_staff
        self.assertTrue(admin.site.has_permission(request))

    def test_pago_admin_restringe_delete_permission_para_no_superusuarios(self):
        """PagoAdmin no debe permitir borrar pagos a usuarios no-superusuarios."""
        pago_admin = admin.site._registry.get(Pago)
        self.assertIsNotNone(pago_admin)
        request = self.factory.get("/admin/pagos/pago/")
        request.user = self.admin_staff
        self.assertFalse(
            pago_admin.has_delete_permission(request),
            "El borrado de pagos debe estar bloqueado para usuarios no-superusuarios",
        )

    def test_pedido_admin_restringe_delete_permission_para_no_superusuarios(self):
        """PedidoAdmin no debe permitir borrar pedidos a usuarios no-superusuarios."""
        pedido_admin = admin.site._registry.get(Pedido)
        self.assertIsNotNone(pedido_admin)
        request = self.factory.get("/admin/pedidos/pedido/")
        request.user = self.admin_staff
        self.assertFalse(
            pedido_admin.has_delete_permission(request),
            "El borrado de pedidos debe estar bloqueado para usuarios no-superusuarios",
        )

    def test_factura_admin_restringe_delete_permission_para_no_superusuarios(self):
        """FacturaAdmin no debe permitir borrar facturas a usuarios no-superusuarios."""
        factura_admin = admin.site._registry.get(Factura)
        self.assertIsNotNone(factura_admin)
        request = self.factory.get("/admin/pagos/factura/")
        request.user = self.admin_staff
        self.assertFalse(
            factura_admin.has_delete_permission(request),
            "El borrado de facturas debe estar bloqueado para usuarios no-superusuarios",
        )

    def test_list_select_related_configurado_en_modelos_criticos(self):
        """Verifica que PagoAdmin y PedidoAdmin tengan list_select_related para evitar N+1 queries."""
        pago_admin = admin.site._registry.get(Pago)
        pedido_admin = admin.site._registry.get(Pedido)
        self.assertTrue(
            bool(pago_admin.list_select_related),
            "PagoAdmin debe tener list_select_related configurado",
        )
        self.assertTrue(
            bool(pedido_admin.list_select_related),
            "PedidoAdmin debe tener list_select_related configurado",
        )
