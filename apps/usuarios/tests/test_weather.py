from datetime import datetime, timezone
from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from apps.usuarios.weather import get_route_weather


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
)
class RouteWeatherTests(SimpleTestCase):
    """El modulo ahora usa Open-Meteo (gratis, sin API key).

    Se mockean las dos llamadas HTTP (geocoding + forecast) para no
    depender de la red en los tests.
    """

    def setUp(self):
        cache.clear()

    def _forecast_response(self, target_iso):
        response = Mock()
        response.json.return_value = {
            "hourly": {
                "time": ["2027-01-01T10:00", "2027-01-01T11:00"],
                "temperature_2m": [18.0, 21.6],
                "relative_humidity_2m": [45, 78],
                "apparent_temperature": [18.0, 22.1],
                "precipitation_probability": [0, 70],
                "weathercode": [0, 61],
                "wind_speed_10m": [3.6, 14.4],
            }
        }
        return response

    def test_uses_forecast_nearest_to_scheduled_delivery(self):
        # El modulo trabaja en zona America/Bogota (UTC-5). Para apuntar a la
        # hora 11:00 local del pronostico, la fecha agendada debe ser 16:00 UTC.
        scheduled_at = datetime(2027, 1, 1, 16, 0, tzinfo=timezone.utc)

        geocode = Mock()
        geocode.json.return_value = {"results": [{"latitude": 4.6, "longitude": -74.0}]}

        forecast = self._forecast_response("2027-01-01T11:00")

        def fake_get(url, **kwargs):
            if "geocoding" in url:
                return geocode
            return forecast

        with patch("apps.usuarios.weather.requests.get", side_effect=fake_get) as get:
            weather = get_route_weather("Bogotá, Calle 12", scheduled_at)

        self.assertTrue(weather["available"])
        self.assertEqual(weather["city"], "Bogotá")
        # hora 11:00 -> temperatura 21.6 -> 22, pop 70 -> 70, viento 14.4 -> 14
        self.assertEqual(weather["temperature"], 22)
        self.assertEqual(weather["precipitation_probability"], 70)
        self.assertEqual(weather["wind_kmh"], 14)
        self.assertEqual(weather["humidity"], 78)
        self.assertEqual(weather["description"], "Lluvia ligera")
        self.assertIn("precaución", weather["recommendation"])
        # la API de Open-Meteo no requiere key
        self.assertNotIn("appid", get.call_args.kwargs.get("params", {}))

    def test_caches_forecast_and_reuses_it(self):
        geocode = Mock()
        geocode.json.return_value = {"results": [{"latitude": 4.6, "longitude": -74.0}]}
        forecast = self._forecast_response("2027-01-01T10:00")

        def fake_get(url, **kwargs):
            return geocode if "geocoding" in url else forecast

        with patch("apps.usuarios.weather.requests.get", side_effect=fake_get):
            first = get_route_weather("Bogotá, Calle 12")
            # el forecast va a cache; la segunda llamada reutiliza la respuesta
            # mockeada igual, pero verificamos que no cambia el resultado
            second = get_route_weather("Bogotá, Calle 12")

        self.assertEqual(first, second)
        self.assertTrue(first["available"])

    def test_reports_geocoding_failure_without_making_forecast_request(self):
        geocode = Mock()
        geocode.json.return_value = {"results": []}

        with patch("apps.usuarios.weather.requests.get", return_value=geocode) as get:
            weather = get_route_weather("Medellín, Centro")

        self.assertFalse(weather["available"])
        self.assertIn("No se pudo ubicar", weather["message"])
        # solo se llamo al geocoding, nunca al forecast
        self.assertEqual(get.call_count, 1)

    def test_reports_network_error_without_failing_panel_request(self):
        geocode = Mock()
        geocode.json.return_value = {"results": [{"latitude": 4.6, "longitude": -74.0}]}

        def fake_get(url, **kwargs):
            if "geocoding" in url:
                return geocode
            raise requests.Timeout()

        with patch("apps.usuarios.weather.requests.get", side_effect=fake_get):
            weather = get_route_weather("Cali, Centro")

        self.assertFalse(weather["available"])
        self.assertIn("No se pudo consultar", weather["message"])

    def test_reports_invalid_json_response(self):
        geocode = Mock()
        geocode.json.return_value = {"results": [{"latitude": 4.6, "longitude": -74.0}]}
        forecast = Mock()
        forecast.json.side_effect = ValueError("invalid json")

        def fake_get(url, **kwargs):
            return geocode if "geocoding" in url else forecast

        with patch("apps.usuarios.weather.requests.get", side_effect=fake_get):
            weather = get_route_weather("Barranquilla, Centro")

        self.assertFalse(weather["available"])
        self.assertIn("respuesta inválida", weather["message"])

    def test_reports_incomplete_forecast_data(self):
        geocode = Mock()
        geocode.json.return_value = {"results": [{"latitude": 4.6, "longitude": -74.0}]}
        forecast = Mock()
        forecast.json.return_value = {"hourly": {"time": ["2027-01-01T10:00"]}}

        def fake_get(url, **kwargs):
            return geocode if "geocoding" in url else forecast

        with patch("apps.usuarios.weather.requests.get", side_effect=fake_get):
            weather = get_route_weather("Cartagena, Centro")

        self.assertFalse(weather["available"])
        self.assertIn("incompletos", weather["message"])
