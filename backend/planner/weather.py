"""Hourly forecast lookup. Values come from the provider payload, never invented."""

from datetime import datetime, timedelta, timezone


def snow_cm_to_inches(cm):
    if cm is None:
        return None
    return cm / 2.54


def sample_at(hourly, eta):
    """hourly keys are ISO hour starts. Returns None if any hazard is missing."""
    if eta.tzinfo is None:
        eta = eta.replace(tzinfo=timezone.utc)
    hour = eta.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    slot = hourly.get(hour.strftime("%Y-%m-%dT%H:%M"))
    if not slot:
        return None
    wind = slot.get("wind_mph")
    rain = slot.get("rain_in_hr")
    snow = slot.get("snow_in_hr")
    if wind is None or rain is None or snow is None:
        return None
    return {"wind_mph": wind, "rain_in_hr": rain, "snow_in_hr": snow}


def forecast_hours_needed(departure, latest_eta):
    if departure.tzinfo is None:
        departure = departure.replace(tzinfo=timezone.utc)
    if latest_eta.tzinfo is None:
        latest_eta = latest_eta.replace(tzinfo=timezone.utc)
    start = departure.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = latest_eta.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return int((end - start).total_seconds() // 3600) + 1


def parse_graphhopper_routes(payload):
    paths = payload.get("paths") or []
    routes = []
    for path in paths:
        points = path.get("points") or {}
        coords = points.get("coordinates") or []
        if len(coords) < 2:
            continue
        routes.append(
            {
                "geometry": coords,
                "distance_meters": path["distance"],
                "duration_seconds": path["time"] / 1000.0,
            }
        )
    if len(routes) < 3:
        raise InsufficientRoutes(len(routes))
    return routes[:3]


class InsufficientRoutes(Exception):
    def __init__(self, count):
        super().__init__("routing API returned {0} route(s); 3 are required".format(count))
        self.count = count


class WeatherProviderError(Exception):
    pass


def require_coverage(hourly, departure, latest_eta):
    needed = forecast_hours_needed(departure, latest_eta)
    hour = departure if departure.tzinfo else departure.replace(tzinfo=timezone.utc)
    hour = hour.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    for _ in range(needed):
        if sample_at(hourly, hour) is None:
            return False
        hour += timedelta(hours=1)
    return True
