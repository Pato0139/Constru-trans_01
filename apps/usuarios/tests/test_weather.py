from datetime import datetime, timezone
from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from usuarios.weather import get_route_weather


@override_settings(
    OPENWEATHER_API_KEY="test-weather-key",
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
)
class RouteWeatherTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_uses_forecast_nearest_to_scheduled_delivery(self):
        scheduled_at = datetime.fromtimestamp(1_800_000_000, tz=timezone.utc)
        response = Mock()
        response.json.return_value = {
            "list": [
                {
                    "dt": 1_799_992_800,
                    "main": {"temp": 18, "feels_like": 18, "humidity": 45},
                    "weather": [{"main": "Clear", "description": "cielo claro", "icon": "01d"}],
                    "wind": {"speed": 1},
                    "pop": 0,
                },
                {
                    "dt": 1_800_003_600,
                    "main": {"temp": 21.6, "feels_like": 22.1, "humidity": 78},
                    "weather": [{"main": "Rain", "description": "lluvia ligera", "icon": "10d"}],
                    "wind": {"speed": 4.0},
                    "pop": 0.7,
                }
            ]
        }

        with patch("usuarios.weather.requests.get", return_value=response) as get:
            weather = get_route_weather("Bogotá, Calle 12", scheduled_at)
            cached_weather = get_route_weather("Bogotá, Calle 12", scheduled_at)

        self.assertTrue(weather["available"])
        self.assertEqual(cached_weather, weather)
        get.assert_called_once()
        self.assertEqual(weather["city"], "Bogotá")
        self.assertEqual(weather["temperature"], 22)
        self.assertEqual(weather["precipitation_probability"], 70)
        self.assertEqual(weather["wind_kmh"], 14)
        self.assertIn("precaución", weather["recommendation"])
        self.assertEqual(get.call_args.kwargs["params"]["q"], "Bogotá,CO")
        self.assertEqual(get.call_args.kwargs["params"]["lang"], "es")
        self.assertNotIn("test-weather-key", weather["icon_url"])

    @override_settings(OPENWEATHER_API_KEY="")
    def test_reports_missing_api_key_without_making_request(self):
        with patch("usuarios.weather.requests.get") as get:
            weather = get_route_weather("Medellín, Centro")

        self.assertFalse(weather["available"])
        self.assertIn("OPENWEATHER_API_KEY", weather["message"])
        get.assert_not_called()

    def test_reports_network_error_without_failing_panel_request(self):
        with patch(
            "usuarios.weather.requests.get",
            side_effect=requests.Timeout(),
        ):
            weather = get_route_weather("Cali, Centro")

        self.assertFalse(weather["available"])
        self.assertIn("No se pudo consultar", weather["message"])

    def test_reports_invalid_json_response(self):
        response = Mock()
        response.json.side_effect = ValueError("invalid json")

        with patch("usuarios.weather.requests.get", return_value=response):
            weather = get_route_weather("Barranquilla, Centro")

        self.assertFalse(weather["available"])
        self.assertIn("respuesta inválida", weather["message"])

    def test_rejects_forecast_outside_available_range(self):
        response = Mock()
        response.json.return_value = {
            "list": [
                {
                    "dt": 1_800_000_000,
                    "main": {"temp": 20, "feels_like": 20, "humidity": 50},
                    "weather": [{"main": "Clear", "description": "cielo claro", "icon": "01d"}],
                    "wind": {"speed": 1},
                    "pop": 0,
                }
            ]
        }
        target = datetime.fromtimestamp(1_900_000_000, tz=timezone.utc)

        with patch("usuarios.weather.requests.get", return_value=response):
            weather = get_route_weather("Cartagena, Centro", target)

        self.assertFalse(weather["available"])
        self.assertIn("fuera del pronóstico", weather["message"])
