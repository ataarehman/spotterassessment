"""HTTP clients. Callers pass responses through; nothing here invents a route or a forecast."""

import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests
from django.conf import settings

from planner.weather import InsufficientRoutes, WeatherProviderError, parse_graphhopper_routes


class GeocodeError(Exception):
    pass


FORECAST_CACHE_TTL_SECONDS = 600
_FORECAST_CACHE = {}


def clear_forecast_cache():
    _FORECAST_CACHE.clear()


def geocode_pair(origin_name, destination_name, session=None):
    with ThreadPoolExecutor(max_workers=2) as pool:
        origin = pool.submit(geocode_place, origin_name, session)
        destination = pool.submit(geocode_place, destination_name, session)
        return origin.result(), destination.result()


def geocode_place(name, session=None):
    http = session or requests
    response = http.get(
        settings.OPEN_METEO_GEOCODE_URL,
        params={"name": name, "count": 1, "language": "en", "format": "json"},
        timeout=20,
    )
    if response.status_code != 200:
        raise GeocodeError("geocoder returned {0}".format(response.status_code))
    results = (response.json() or {}).get("results") or []
    if not results:
        raise GeocodeError("no match for {0}".format(name))
    hit = results[0]
    return {
        "label": hit.get("name"),
        "lat": hit["latitude"],
        "lng": hit["longitude"],
    }


def fetch_routes(origin, destination, session=None):
    if not settings.GRAPHHOPPER_API_KEY:
        raise WeatherProviderError("GRAPHHOPPER_API_KEY is not configured")
    http = session or requests
    response = http.get(
        settings.GRAPHHOPPER_ROUTE_URL,
        params={
            "point": ["{0},{1}".format(origin["lat"], origin["lng"]), "{0},{1}".format(destination["lat"], destination["lng"])],
            "profile": settings.GRAPHHOPPER_PROFILE,
            "algorithm": "alternative_route",
            "alternative_route.max_paths": 3,
            "alternative_route.max_weight_factor": 1.8,
            "points_encoded": "false",
            "key": settings.GRAPHHOPPER_API_KEY,
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise WeatherProviderError("graphhopper returned {0}".format(response.status_code))
    return parse_graphhopper_routes(response.json())


def fetch_forecasts(points, start_iso, hours, session=None, sleeper=time.sleep, use_cache=None):
    if not points:
        raise WeatherProviderError("no forecast points")
    http = session or requests
    forecast_days = _forecast_days(start_iso, hours)
    maps = []
    missing = []
    use_cache = session is None if use_cache is None else use_cache
    for point in points:
        cached = _cache_get(_point_key(point, forecast_days)) if use_cache else None
        if cached is None or start_iso not in cached:
            missing.append(point)
            maps.append(None)
        else:
            maps.append(cached)
    if not missing:
        return maps
    fetched = []
    for offset in range(0, len(missing), 8):
        chunk = missing[offset:offset + 8]
        response = _get_with_backoff(
            http,
            settings.OPEN_METEO_FORECAST_URL,
            {
                "latitude": ",".join(str(point["lat"]) for point in chunk),
                "longitude": ",".join(str(point["lng"]) for point in chunk),
                "hourly": "wind_speed_10m,precipitation,snowfall",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "UTC",
                "forecast_days": forecast_days,
            },
            sleeper,
        )
        if response.status_code != 200:
            raise WeatherProviderError("open-meteo returned {0}".format(response.status_code))
        payload = response.json()
        blocks = payload if isinstance(payload, list) else [payload]
        if len(blocks) != len(chunk):
            raise WeatherProviderError("open-meteo returned {0} locations for {1} points".format(len(blocks), len(chunk)))
        for point, block in zip(chunk, blocks):
            hourly = _hourly_map(block)
            if use_cache:
                _cache_put(_point_key(point, forecast_days), hourly)
            fetched.append(hourly)
    fill = iter(fetched)
    return [item if item is not None else next(fill) for item in maps]


def _get_with_backoff(http, url, params, sleeper):
    delay = 0.5
    response = None
    for attempt in range(4):
        response = http.get(url, params=params, timeout=30)
        if response.status_code not in (429, 503):
            return response
        if attempt == 3:
            return response
        sleeper(delay + random.uniform(0, delay * 0.25))
        delay = min(delay * 2, 8)
    return response


def _point_key(point, forecast_days):
    return (round(point["lat"], 2), round(point["lng"], 2), forecast_days)


def _cache_get(key):
    item = _FORECAST_CACHE.get(key)
    if item is None:
        return None
    stored_at, payload = item
    if time.time() - stored_at > FORECAST_CACHE_TTL_SECONDS:
        del _FORECAST_CACHE[key]
        return None
    return payload


def _cache_put(key, payload):
    _FORECAST_CACHE[key] = (time.time(), payload)


def _forecast_days(start_iso, hours):
    start = datetime.fromisoformat(start_iso).replace(tzinfo=timezone.utc)
    end = start + timedelta(hours=hours)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return min(16, max(1, (end - today).days + 1))


def _hourly_map(block):
    hourly = block.get("hourly") or {}
    times = hourly.get("time") or []
    wind = hourly.get("wind_speed_10m") or []
    rain = hourly.get("precipitation") or []
    snow = hourly.get("snowfall") or []
    mapped = {}
    snow_unit = ((block.get("hourly_units") or {}).get("snowfall") or "cm").lower()
    for index, stamp in enumerate(times):
        key = stamp[:16]
        snow_value = snow[index] if index < len(snow) else None
        if snow_value is None:
            snow_in = None
        elif snow_unit in ("cm", "centimeter", "centimeters"):
            snow_in = snow_value / 2.54
        else:
            snow_in = snow_value
        mapped[key] = {
            "wind_mph": wind[index] if index < len(wind) else None,
            "rain_in_hr": rain[index] if index < len(rain) else None,
            "snow_in_hr": snow_in,
        }
    return mapped
