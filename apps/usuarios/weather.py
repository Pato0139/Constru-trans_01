import logging
from datetime import datetime, timezone as datetime_timezone

import requests
from django.core.cache import cache
from django.utils import timezone

from config.despacho import separar_direccion_destino

logger = logging.getLogger(__name__)

# Open-Meteo: API de pronostico gratuita, sin API key ni registro.
# Documentacion: https://open-meteo.com/en/docs
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
FORECAST_CACHE_SECONDS = 600

# Mapeo de codigos WMO (weathercode de Open-Meteo) a descripcion en espanol
# y a un icono equivalente de OpenWeather (el template usa icon_url de OWM).
WMO_MAP = {
    0: ("Cielo despejado", "01"),
    1: ("Mayormente despejado", "02"),
    2: ("Parcialmente nublado", "03"),
    3: ("Nublado", "04"),
    45: ("Niebla", "50"),
    48: ("Niebla con escarcha", "50"),
    51: ("Llovizna ligera", "09"),
    53: ("Llovizna moderada", "09"),
    55: ("Llovizna densa", "09"),
    56: ("Llovizna helada ligera", "09"),
    57: ("Llovizna helada densa", "09"),
    61: ("Lluvia ligera", "10"),
    63: ("Lluvia moderada", "10"),
    65: ("Lluvia fuerte", "10"),
    66: ("Lluvia helada ligera", "10"),
    67: ("Lluvia helada fuerte", "10"),
    71: ("Nevada ligera", "13"),
    73: ("Nevada moderada", "13"),
    75: ("Nevada fuerte", "13"),
    77: ("Granizo", "13"),
    80: ("Chubascos ligeros", "09"),
    81: ("Chubascos moderados", "09"),
    82: ("Chubascos violentos", "09"),
    85: "Nevadas ligeras",
    86: "Nevadas fuertes",
    95: "Tormenta electrica",
    96: "Tormenta con granizo leve",
    99: "Tormenta con granizo fuerte",
}
# Algunos valores se guardaron como texto plano por error de tipeo; normalizar
# para que todos sean tuplas (descripcion, codigo_icono_base).
WMO_MAP = {k: (v if isinstance(v, tuple) else (v, "11")) for k, v in WMO_MAP.items()}


def _unavailable(city, message):
    return {"available": False, "city": city, "message": message}


def _geocode(city):
    """Convierte el nombre de la ciudad en coordenadas (lat, lon)."""
    try:
        response = requests.get(
            GEOCODING_URL,
            params={"name": city, "count": 1, "language": "es", "format": "json"},
            timeout=(5, 10),
        )
        response.raise_for_status()
        data = response.json()
    except ValueError:
        logger.warning("Open-Meteo geocoding devolvio JSON invalido para %s", city)
        return None
    except requests.RequestException as exc:
        logger.warning(
            "Open-Meteo geocoding fallo para %s (%s)", city, type(exc).__name__
        )
        return None

    results = data.get("results") if isinstance(data, dict) else None
    if not results:
        logger.info("Open-Meteo geocoding sin resultados para %s", city)
        return None

    first = results[0]
    try:
        return float(first["latitude"]), float(first["longitude"])
    except (KeyError, TypeError, ValueError):
        logger.warning("Open-Meteo geocoding devolvio coordenadas invalidas para %s", city)
        return None


def get_route_weather(destination, scheduled_at=None):
    city, _ = separar_direccion_destino(destination)
    if not city:
        return _unavailable("", "No se pudo identificar la ciudad de destino.")

    coords = _geocode(city)
    if coords is None:
        return _unavailable(
            city, "No se pudo ubicar la ciudad de destino en el mapa."
        )
    latitude, longitude = coords

    cache_key = "openmeteo_forecast_" + str(latitude) + "_" + str(longitude)
    forecast = cache.get(cache_key)
    if forecast is None:
        try:
            response = requests.get(
                FORECAST_URL,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    # variables por hora necesarias para el panel
                    "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,weathercode,wind_speed_10m",
                    "timezone": "America/Bogota",
                    "forecast_days": 7,
                },
                timeout=(5, 12),
            )
            response.raise_for_status()
            forecast = response.json()
        except ValueError as exc:
            logger.warning(
                "Open-Meteo devolvio JSON invalido para %s (%s)",
                city,
                type(exc).__name__,
            )
            return _unavailable(city, "El servicio del clima devolvió una respuesta inválida.")
        except requests.RequestException as exc:
            logger.warning(
                "Open-Meteo forecast fallo para %s (%s)", city, type(exc).__name__
            )
            return _unavailable(
                city, "No se pudo consultar el pronóstico. Intenta de nuevo más tarde."
            )

        hourly = forecast.get("hourly") if isinstance(forecast, dict) else None
        if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
            logger.warning("Open-Meteo devolvio una estructura invalida para %s", city)
            return _unavailable(city, "No se recibió un pronóstico válido para esta ciudad.")
        cache.set(cache_key, forecast, FORECAST_CACHE_SECONDS)

    hourly = forecast["hourly"]
    times = hourly.get("time") or []

    target_time = scheduled_at or timezone.now()
    if timezone.is_naive(target_time):
        target_time = timezone.make_aware(target_time)
    # Open-Meteo devuelve las horas en la zona pedida (America/Bogota).
    target_local = timezone.localtime(target_time)
    target_iso = target_local.strftime("%Y-%m-%dT%H:00")

    # Buscar la hora del pronostico mas cercana a la entrega programada.
    selected_index = None
    for i, t in enumerate(times):
        if t == target_iso:
            selected_index = i
            break
    if selected_index is None:
        # si no hay coincidencia exacta, tomar la mas cercana disponible
        target_ts = target_local.timestamp()
        best = None
        best_diff = None
        for i, t in enumerate(times):
            try:
                item_ts = datetime.fromisoformat(t).timestamp()
            except (TypeError, ValueError):
                continue
            diff = abs(item_ts - target_ts)
            if best_diff is None or diff < best_diff:
                best_diff = diff
                best = i
        selected_index = best

    if selected_index is None:
        return _unavailable(
            city, "No hay datos disponibles para el pronóstico de esta ruta."
        )

    def _at(key):
        values = hourly.get(key)
        if isinstance(values, list) and selected_index < len(values):
            return values[selected_index]
        return None

    try:
        temperature = round(float(_at("temperature_2m")))
        feels_like = round(float(_at("apparent_temperature")))
        humidity = int(round(float(_at("relative_humidity_2m"))))
        wind_speed_kmh = round(float(_at("wind_speed_10m")))
        pop_raw = _at("precipitation_probability")
        precipitation_probability = int(round(float(pop_raw))) if pop_raw is not None else 0
        wmo_code = int(_at("weathercode"))
        forecast_time = datetime.fromisoformat(times[selected_index])
    except (KeyError, IndexError, TypeError, ValueError, OverflowError) as exc:
        logger.warning(
            "Open-Meteo devolvio datos incompletos para %s (%s)",
            city,
            type(exc).__name__,
        )
        return _unavailable(city, "Los datos recibidos del pronóstico están incompletos.")

    description, icon_base = WMO_MAP.get(wmo_code, ("Condición variable", "03"))
    # Elegir variante dia/noche para el icono (coincide con la hora local de la entrega)
    suffix = "d" if 6 <= target_local.hour < 18 else "n"
    icon = icon_base + suffix
    icon_url = f"https://openweathermap.org/img/wn/{icon}@2x.png"

    if wmo_code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}:
        recommendation = "Se prevé precipitación. Revisa la visibilidad y conduce con precaución."
    elif wind_speed_kmh >= 35:
        recommendation = "Se prevé viento fuerte. Asegura la carga y conduce con precaución."
    elif wmo_code in {45, 48}:
        recommendation = "Hay niebla en la zona. Enciende las luces y reduce la velocidad."
    else:
        recommendation = "Revisa las condiciones al salir; el pronóstico puede cambiar."

    return {
        "available": True,
        "city": city,
        "forecast_time": timezone.make_aware(forecast_time),
        "temperature": temperature,
        "feels_like": feels_like,
        "humidity": humidity,
        "wind_kmh": wind_speed_kmh,
        "precipitation_probability": precipitation_probability,
        "description": description,
        "icon_url": icon_url,
        "recommendation": recommendation,
    }
