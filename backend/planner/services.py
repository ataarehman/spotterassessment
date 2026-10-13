"""Compose geocoding, routing, arrival weather, risk, and ranking."""

import time
from datetime import datetime, timedelta, timezone

from planner.checkpoints import checkpoints
from planner.clients import GeocodeError, fetch_forecasts, fetch_routes, geocode_pair
from planner.ranking import rank, summarize
from planner.risk import apply_load, classify_rain, classify_snow, classify_wind, combine
from planner.weather import InsufficientRoutes, WeatherProviderError, forecast_hours_needed, sample_at


class PlanError(Exception):
    def __init__(self, code, message, status):
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message


def build_plan(payload, session=None):
    origin_name = (payload.get("origin") or "").strip()
    destination_name = (payload.get("destination") or "").strip()
    spacing = payload.get("spacing_miles")
    weight = payload.get("weight_lb")
    departure_raw = payload.get("departure")
    if not origin_name or not destination_name:
        raise PlanError("invalid_input", "Origin and destination are required.", 400)
    if spacing not in (10, 25, 50):
        raise PlanError("invalid_input", "spacing_miles must be 10, 25, or 50.", 400)
    try:
        weight = float(weight)
    except (TypeError, ValueError):
        raise PlanError("invalid_input", "weight_lb must be a number.", 400)
    if weight < 0:
        raise PlanError("invalid_input", "weight_lb must be non-negative.", 400)
    try:
        departure = datetime.fromisoformat(departure_raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        raise PlanError("invalid_input", "departure must be an ISO-8601 datetime.", 400)
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)

    timings = {}
    started = time.perf_counter()
    try:
        mark = time.perf_counter()
        origin, destination = geocode_pair(origin_name, destination_name, session=session)
        timings["geocode_ms"] = int((time.perf_counter() - mark) * 1000)
        mark = time.perf_counter()
        raw_routes = fetch_routes(origin, destination, session=session)
        timings["routing_ms"] = int((time.perf_counter() - mark) * 1000)
    except GeocodeError as exc:
        raise PlanError("geocode_failed", str(exc), 404)
    except InsufficientRoutes as exc:
        raise PlanError("insufficient_routes", str(exc), 502)
    except WeatherProviderError as exc:
        raise PlanError("provider_unavailable", str(exc), 502)

    built = []
    for index, route in enumerate(raw_routes):
        stops = checkpoints(route["geometry"], spacing, departure, route["duration_seconds"])
        built.append(
            {
                "id": "route-{0}".format(index + 1),
                "geometry": route["geometry"],
                "distance_meters": route["distance_meters"],
                "duration_seconds": route["duration_seconds"],
                "stops": stops,
            }
        )

    latest = max(stop["eta"] for route in built for stop in route["stops"])
    hours = max(49, forecast_hours_needed(departure, latest))
    sample_points = []
    seen = set()
    for route in built:
        for stop in route["stops"]:
            key = (round(stop["lat"], 2), round(stop["lng"], 2))
            if key in seen:
                continue
            seen.add(key)
            sample_points.append({"lat": key[0], "lng": key[1], "key": key})

    start_hour = departure.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    try:
        mark = time.perf_counter()
        forecasts = fetch_forecasts(
            sample_points,
            start_hour.strftime("%Y-%m-%dT%H:%M"),
            hours,
            session=session,
        )
    except WeatherProviderError as exc:
        raise PlanError("provider_unavailable", str(exc), 502)
    timings["weather_ms"] = int((time.perf_counter() - mark) * 1000)
    from planner.clients import LAST_FORECAST_CALLS

    timings["weather_requests"] = list(LAST_FORECAST_CALLS)

    mark = time.perf_counter()
    by_key = {point["key"]: forecasts[index] for index, point in enumerate(sample_points)}
    for route in built:
        for stop in route["stops"]:
            key = (round(stop["lat"], 2), round(stop["lng"], 2))
            sample = sample_at(by_key[key], stop["eta"])
            stop["weather"] = sample
            if sample is None:
                stop["risk"] = None
                continue
            wind = apply_load(classify_wind(sample["wind_mph"]), sample["wind_mph"], weight)
            stop["risk"] = combine(
                wind,
                classify_rain(sample["rain_in_hr"]),
                classify_snow(sample["snow_in_hr"]),
            )
        route["summary"] = summarize(
            [{"distance_miles": stop["distance_miles"], "risk": stop["risk"]} for stop in route["stops"]]
        )

    ordered, recommended = rank(built)
    heatmap = []
    for point in sample_points:
        hours_out = []
        cursor = start_hour
        for _ in range(49):
            sample = sample_at(by_key[point["key"]], cursor)
            hours_out.append(sample)
            cursor += timedelta(hours=1)
        heatmap.append({"lat": point["lat"], "lng": point["lng"], "hours": hours_out})

    timings["risk_ms"] = int((time.perf_counter() - mark) * 1000)
    timings["total_ms"] = int((time.perf_counter() - started) * 1000)

    return {
        "origin": origin,
        "destination": destination,
        "departure": departure.isoformat(),
        "weight_lb": weight,
        "spacing_miles": spacing,
        "routing_provider": "graphhopper",
        "profile": settings_profile(),
        "recommended_route_id": recommended,
        "routes": [_public_route(route) for route in ordered],
        "heatmap": heatmap,
        "timings_ms": timings,
    }


def settings_profile():
    from django.conf import settings

    return settings.GRAPHHOPPER_PROFILE


def _public_route(route):
    return {
        "id": route["id"],
        "geometry": {"type": "LineString", "coordinates": route["geometry"]},
        "distance_meters": route["distance_meters"],
        "duration_seconds": route["duration_seconds"],
        "summary": route["summary"],
        "checkpoints": [
            {
                "distance_miles": stop["distance_miles"],
                "eta": stop["eta"].isoformat(),
                "lng": stop["lng"],
                "lat": stop["lat"],
                "weather": stop["weather"],
                "risk": stop["risk"],
            }
            for stop in route["stops"]
        ],
    }
