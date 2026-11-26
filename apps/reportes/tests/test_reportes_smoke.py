import xml.etree.ElementTree as ET
from decimal import Decimal
from io import BytesIO

import openpyxl
from django.test import Client, TestCase
from django.urls import reverse

from apps.catalogo.models import Catalogo, MaterialConstruccion, UnidadMedida
from apps.clientes.models import Cliente
from apps.pedidos.models import DetallePedido, Pedido
from apps.usuarios.models import Usuario


class SmokeViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username="adminsmoke",
            email="adminsmoke@test.com",
            password="password123",
            nombres="Admin",
            apellidos="Smoke",
            documento="555444333",
            tipo_documento="CC",
            rol="admin",
        )

    def test_ruta_carga(self):
        self.client.login(username="adminsmoke", password="password123")
        response = self.client.get(reverse("reportes:reportes_admin"))
        self.assertEqual(response.status_code, 200)


class ReportExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        admin = Usuario.objects.create_user(
            username="adminreports",
            email="adminreports@test.com",
            password="password123",
            nombres="Admin",
            apellidos="Reportes",
            documento="555444334",
            tipo_documento="CC",
            rol="admin",
        )
        self.client.login(username=admin.username, password="password123")

        customer_user = Usuario.objects.create_user(
            username="clientereports",
            email="cliente@test.com",
            password="password123",
            nombres="Maria",
            apellidos="Pruebas",
            documento="111222333",
            tipo_documento="CC",
            rol="cliente",
            telefono="3001234567",
        )
        customer, _ = Cliente.ensure_for_user(customer_user)
        catalog = Catalogo.objects.create(codigo_catalogo="CEM", nombre_empresa="Cementos")
        unit = UnidadMedida.objects.create(
            codigo="UND",
            nombre="Unidad",
            abreviatura="u",
        )
        self.material_name = "Material de Construccion de Prueba Extra Larga para validar descargas"
        material = MaterialConstruccion.objects.create(
            catalogo=catalog,
            nombre=self.material_name,
            unidad_medida=unit,
            descripcion="Material para probar los reportes.",
            precio_referencia=Decimal("1234.56"),
            stock=12,
        )
        self.order = Pedido.objects.create(
            usuario=customer_user,
            cliente=customer,
            estado="pendiente",
        )
        DetallePedido.objects.create(
            pedido=self.order,
            material=material,
            cantidad=3,
            precio_unitario=Decimal("1234.56"),
        )
        self.order.refresh_from_db()

    def test_campos_de_reportes_excel_y_xml_coinciden(self):
        report_fields = {
            "clientes": (
                ["id", "nombre", "email", "telefono", "estado"],
                ["ID", "Nombre", "Correo", "Teléfono", "Estado"],
            ),
            "materiales": (
                ["id", "nombre", "tipo", "precio", "stock"],
                ["ID", "Nombre", "Tipo", "Precio", "Stock"],
            ),
            "ventas": (
                ["id", "cliente", "fecha", "total", "estado"],
                ["ID", "Cliente", "Fecha", "Total", "Estado"],
            ),
            "pedidos": (
                ["id", "cliente", "fecha", "materiales", "total", "estado"],
                ["ID", "Cliente", "Fecha", "Materiales", "Total", "Estado"],
            ),
        }

        for tipo, (fields, labels) in report_fields.items():
            with self.subTest(tipo=tipo):
                excel_response = self.client.get(
                    reverse("reportes:exportar_reporte_excel", args=[tipo])
                )
                self.assertEqual(excel_response.status_code, 200)
                workbook = openpyxl.load_workbook(BytesIO(excel_response.content))
                worksheet = workbook.active
                headers = [cell.value for cell in worksheet[1]]
                self.assertEqual(headers, labels)

                xml_response = self.client.get(
                    reverse("reportes:exportar_reporte_xml", args=[tipo])
                )
                self.assertEqual(xml_response.status_code, 200)
                root = ET.fromstring(xml_response.content)
                item = root[0]
                self.assertEqual([child.tag for child in item if child.tag != "detalles"], fields)

        order_sheet = openpyxl.load_workbook(
            BytesIO(
                self.client.get(
                    reverse("reportes:exportar_reporte_excel", args=["pedidos"])
                ).content
            )
        ).active
        order_row = [cell.value for cell in order_sheet[2]]
        self.assertIn(self.material_name, order_row[3])

        orders_xml = ET.fromstring(
            self.client.get(reverse("reportes:exportar_reporte_xml", args=["pedidos"])).content
        )
        self.assertIn(self.material_name, orders_xml[0].findtext("materiales"))
        self.assertTrue(orders_xml[0].findtext("fecha"))
        self.assertEqual(orders_xml[0].findtext("detalles/detalle/cantidad"), "3")

    def test_pdf_incluye_logo(self):
        response = self.client.get(reverse("reportes:exportar_reporte_pdf", args=["pedidos"]))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn(b"/Subtype /Image", response.content)
