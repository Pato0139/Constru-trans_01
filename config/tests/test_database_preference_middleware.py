from unittest.mock import patch

from django.db import connections
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from config.db_preference import PREF_LOCAL, PREF_REMOTA, get_db_preference
from config.middleware import DatabasePreferenceMiddleware


class DatabasePreferenceMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get(
            "/usuarios/panel/",
            HTTP_COOKIE="bd_preferida=local",
        )
        self.request.session = {}

    def test_missing_local_pedido_table_falls_back_to_remote(self):
        selected_preferences = []

        def get_response(request):
            selected_preferences.append(get_db_preference())
            return HttpResponse()

        with (
            patch.object(
                connections["local"].introspection,
                "table_names",
                return_value=[],
            ),
            patch("config.middleware.conexion_remota_disponible", return_value=True),
        ):
            response = DatabasePreferenceMiddleware(get_response)(self.request)

        self.assertEqual(selected_preferences, [PREF_REMOTA])
        self.assertEqual(self.request.session["bd_preferida"], PREF_REMOTA)
        self.assertEqual(response.cookies["bd_preferida"].value, PREF_REMOTA)

    def test_existing_local_pedido_table_preserves_local_preference(self):
        selected_preferences = []

        def get_response(request):
            selected_preferences.append(get_db_preference())
            return HttpResponse()

        with (
            patch.object(
                connections["local"].introspection,
                "table_names",
                return_value=["pedido"],
            ),
            patch("config.middleware.conexion_remota_disponible", return_value=True),
        ):
            response = DatabasePreferenceMiddleware(get_response)(self.request)

        self.assertEqual(selected_preferences, [PREF_LOCAL])
        self.assertNotIn("bd_preferida", response.cookies)
