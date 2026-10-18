"""
Pruebas de Seguridad: Configuración, Cabeceras y Exposición de Información (Área 5)
Verifica:
1. X_FRAME_OPTIONS configurado a DENY y SECURE_BROWSER_X_FRAME_OPTIONS eliminado.
2. Cabeceras nosniff y referrer policy configuradas.
3. Handlers personalizados 400, 403, 404 y 500 que no revelan stack traces ni rutas internas.
4. Exportación XML usando defusedxml para prevenir XXE.
5. Content Security Policy (CSP) en modo Report-Only configurada.
"""

from unittest.mock import patch
from django.conf import settings
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import resolve, reverse

from config.views import error_400, error_403, error_404, error_500


class SeguridadArea5ConfigHeadersTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_x_frame_options_es_deny_y_no_existe_setting_obsoleto(self):
        """Verifica que X_FRAME_OPTIONS='DENY' y no se usa el setting inventado SECURE_BROWSER_X_FRAME_OPTIONS."""
        self.assertEqual(getattr(settings, "X_FRAME_OPTIONS", None), "DENY")
        self.assertFalse(
            hasattr(settings, "SECURE_BROWSER_X_FRAME_OPTIONS"),
            "SECURE_BROWSER_X_FRAME_OPTIONS no debe existir; Django usa X_FRAME_OPTIONS",
        )

    def test_cabeceras_nosniff_y_referrer_configuradas(self):
        """Verifica que nosniff y referrer policy estén activas en settings."""
        self.assertTrue(getattr(settings, "SECURE_CONTENT_TYPE_NOSNIFF", False))
        self.assertEqual(
            getattr(settings, "SECURE_REFERRER_POLICY", ""),
            "strict-origin-when-cross-origin",
        )

    def test_handlers_de_error_personalizados_configurados_en_urls(self):
        """Verifica que config.urls defina handlers personalizados para 400, 403, 404 y 500."""
        import config.urls as urls_mod
        self.assertEqual(urls_mod.handler400, "config.views.error_400")
        self.assertEqual(urls_mod.handler403, "config.views.error_403")
        self.assertEqual(urls_mod.handler404, "config.views.error_404")
        self.assertEqual(urls_mod.handler500, "config.views.error_500")

    def test_handler500_no_revela_stack_trace_en_ajax(self):
        """El handler 500 en petición AJAX debe devolver JSON limpio sin filtrar excepciones internas."""
        import json
        request = self.factory.get("/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        response = error_500(request)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers.get("Content-Type"), "application/json")
        data = json.loads(response.content)
        self.assertIn("error", data)
        self.assertNotIn("Traceback", str(data))
        self.assertNotIn("File ", str(data))

    def test_exportacion_xml_no_importa_minidom_inseguro(self):
        """Verifica que apps.reportes.views use defusedxml en lugar del minidom de stdlib."""
        import inspect
        from apps.reportes import views as rep_views
        source = inspect.getsource(rep_views.exportar_reporte_xml)
        self.assertIn("defusedxml", source)
        self.assertNotIn("from xml.dom import minidom", source)

    def test_csp_configurado_en_modo_report_only(self):
        """Verifica que CSP_REPORT_ONLY esté activo para no romper recursos existentes."""
        self.assertTrue(getattr(settings, "CSP_REPORT_ONLY", False))
