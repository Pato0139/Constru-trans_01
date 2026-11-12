from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from config.db_preference import PREF_LOCAL, get_db_preference
from config.middleware import DatabasePreferenceMiddleware


class DatabasePreferenceMiddlewareTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().get(
            "/usuarios/panel/",
            HTTP_COOKIE="bd_preferida=local",
        )
        self.request.session = {}

    def test_missing_local_pedido_table_does_not_force_remote(self):
        selected_preferences = []

        def get_response(request):
            selected_preferences.append(get_db_preference())
            return HttpResponse()

        with patch("config.middleware.conexion_remota_disponible", return_value=True):
            response = DatabasePreferenceMiddleware(get_response)(self.request)

        self.assertEqual(selected_preferences, [PREF_LOCAL])
        self.assertNotIn("bd_preferida", self.request.session)
        self.assertNotIn("bd_preferida", response.cookies)

    def test_existing_local_pedido_table_preserves_local_preference(self):
        selected_preferences = []

        def get_response(request):
            selected_preferences.append(get_db_preference())
            return HttpResponse()

        with patch("config.middleware.conexion_remota_disponible", return_value=True):
            response = DatabasePreferenceMiddleware(get_response)(self.request)

        self.assertEqual(selected_preferences, [PREF_LOCAL])
        self.assertNotIn("bd_preferida", response.cookies)
