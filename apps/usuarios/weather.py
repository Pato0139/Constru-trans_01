import hashlib
import logging
import re
from datetime import datetime, timezone as datetime_timezone

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from config.despacho import separar_direccion_destino

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
FORECAST_CACHE_SECONDS = 600
MAX_FORECAST_DISTANCE_SECONDS = 4 * 60 * 60


def _unavailable(city, message):
    return {"available": False, "city": city, "message": message}


def get_route_weather(destination, scheduled_at=None):
    city, _ = separar_direccion_destino(destination)
    if not city:
        return _unavailable("", "No se pudo identificar la ciudad de destino.")

    api_key = settings.OPENWEATHER_API_KEY.strip()
    if not api_key:
        return _unavailable(
            city,
            "El servicio del clima no está configurado. Agrega OPENWEATHER_API_KEY al archivo .env.",
        )

    cache_key = "openweather_forecast_" + hashlib.sha256(
        city.casefold().encode("utf-8")
    ).hexdigest()[:16]
    forecast = cache.get(cache_key)
    if forecast is None:
        try:
            response = requests.get(
                FORECAST_URL,
                params={
                    "q": f"{city},CO",
                    "appid": api_key,
                    "units": "metric",
                    "lang": "es",
                },
                timeout=(2, 4),
            )
            response.raise_for_status()
            forecast = response.json()
        except ValueError as exc:
            logger.warning(
                "OpenWeather returned invalid JSON for %s (%s)",
                city,
                type(exc).__name__,
            )
            return _unavailable(city, "El servicio del clima devolvió una respuesta inválida.")
        except requests.RequestException as exc:
            logger.warning(
                "OpenWeather forecast request failed for %s (%s)",
                city,
                type(exc).__name__,
            )
            return _unavailable(
                city,
                "No se pudo consultar el pronóstico. Intenta de nuevo más tarde.",
            )

        if not isinstance(forecast, dict) or not isinstance(forecast.get("list"), list):
            logger.warning("OpenWeather returned an invalid forecast structure for %s", city)
            return _unavailable(city, "No se recibió un pronóstico válido para esta ciudad.")
        cache.set(cache_key, forecast, FORECAST_CACHE_SECONDS)

    target_time = scheduled_at or timezone.now()
    if timezone.is_naive(target_time):
        target_time = timezone.make_aware(target_time)
    target_timestamp = target_time.timestamp()

    candidates = [
        item
        for item in forecast["list"]
        if isinstance(item, dict) and isinstance(item.get("dt"), (int, float))
    ]
    if not candidates:
        return _unavailable(city, "No hay datos disponibles para el pronóstico de esta ruta.")

    selected = min(candidates, key=lambda item: abs(item["dt"] - target_timestamp))
    if abs(selected["dt"] - target_timestamp) > MAX_FORECAST_DISTANCE_SECONDS:
        return _unavailable(
            city,
            "La fecha de esta ruta queda fuera del pronóstico disponible de 5 días.",
        )

    try:
        temperature = round(float(selected["main"]["temp"]))
        feels_like = round(float(selected["main"]["feels_like"]))
        humidity = int(selected["main"]["humidity"])
        wind_speed = float(selected["wind"]["speed"])
        weather_condition = selected["weather"][0]
        description = str(weather_condition["description"]).strip().capitalize()
        icon = str(weather_condition["icon"])
        precipitation_probability = round(float(selected.get("pop", 0)) * 100)
        forecast_time = datetime.fromtimestamp(
            selected["dt"],
            tz=datetime_timezone.utc,
        )
    except (KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
        logger.warning(
            "OpenWeather returned incomplete forecast data for %s (%s)",
            city,
            type(exc).__name__,
        )
        return _unavailable(city, "Los datos recibidos del pronóstico están incompletos.")

    if not re.fullmatch(r"\d{2}[dn]", icon):
        icon = ""

    condition = str(weather_condition.get("main", "")).casefold()
    wind_kmh = round(wind_speed * 3.6)
    if condition in {"rain", "drizzle", "thunderstorm", "snow"} or precipitation_probability >= 50:
        recommendation = "Se prevé precipitación. Revisa la visibilidad y conduce con precaución."
    elif wind_kmh >= 35:
        recommendation = "Se prevé viento fuerte. Asegura la carga y conduce con precaución."
    else:
        recommendation = "Revisa las condiciones al salir; el pronóstico puede cambiar."

    return {
        "available": True,
        "city": city,
        "forecast_time": timezone.localtime(forecast_time),
        "temperature": temperature,
        "feels_like": feels_like,
        "humidity": humidity,
        "wind_kmh": wind_kmh,
        "precipitation_probability": precipitation_probability,
        "description": description,
        "icon_url": f"https://openweathermap.org/img/wn/{icon}@2x.png" if icon else "",
        "recommendation": recommendation,
    }
