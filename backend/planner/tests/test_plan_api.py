from datetime import datetime, timedelta, timezone

import pytest
from django.test import Client

from planner.services import build_plan


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, routes=3, null_wind=False):
        self.routes = routes
        self.null_wind = null_wind
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(url)
        if "search" in url:
            name = params["name"]
            lat = 32.7 if "Dallas" in name else 41.8
            lng = -96.8 if "Dallas" in name else -87.6
            return FakeResponse(200, {"results": [{"name": name, "latitude": lat, "longitude": lng}]})
        if "route" in url:
            paths = []
            for index in range(self.routes):
                shift = index * 0.3
                paths.append(
                    {
                        "distance": 100000 + index,
                        "time": 3600000,
                        "points": {
                            "coordinates": [
                                [-96.8, 32.7],
                                [-96.8 + shift, 37.0],
                                [-87.6, 41.8],
                            ]
                        },
                    }
                )
            return FakeResponse(200, {"paths": paths})
        times = []
        start = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
        for hour in range(80):
            times.append((start + timedelta(hours=hour)).strftime("%Y-%m-%dT%H:%M"))
        wind = [None if self.null_wind else 10 for _ in times]
        block = {
            "hourly": {
                "time": times,
                "wind_speed_10m": wind,
                "precipitation": [0 for _ in times],
                "snowfall": [0 for _ in times],
            }
        }
        count = len(params["latitude"].split(","))
        return FakeResponse(200, [block for _ in range(count)] if count > 1 else block)


@pytest.fixture
def session(settings):
    settings.GRAPHHOPPER_API_KEY = "test-key"
    return FakeSession()


def test_plan_api_with_fakes(session):
    plan = build_plan(
        {
            "origin": "Dallas",
            "destination": "Chicago",
            "departure": "2026-10-13T12:00:00Z",
            "weight_lb": 42000,
            "spacing_miles": 50,
        },
        session=session,
    )
    assert len(plan["routes"]) == 3
    assert plan["recommended_route_id"]
    first = plan["routes"][0]["checkpoints"][0]
    assert first["risk"] == "Low"
    assert first["weather"]["wind_mph"] == 10
    assert len(plan["heatmap"][0]["hours"]) == 49


def test_missing_weather_blocks_recommendation(settings):
    settings.GRAPHHOPPER_API_KEY = "test-key"
    plan = build_plan(
        {
            "origin": "Dallas",
            "destination": "Chicago",
            "departure": "2026-10-13T12:00:00Z",
            "weight_lb": 10000,
            "spacing_miles": 50,
        },
        session=FakeSession(null_wind=True),
    )
    assert plan["recommended_route_id"] is None
    assert plan["routes"][0]["checkpoints"][0]["risk"] is None


def test_fewer_than_three_routes_is_an_error(settings, monkeypatch):
    settings.GRAPHHOPPER_API_KEY = "test-key"
    from planner.weather import InsufficientRoutes

    monkeypatch.setattr(
        "planner.services.geocode_pair",
        lambda origin, destination, session=None: (
            {"label": origin, "lat": 1, "lng": 2},
            {"label": destination, "lat": 3, "lng": 4},
        ),
    )

    def boom(*args, **kwargs):
        raise InsufficientRoutes(2)

    monkeypatch.setattr("planner.services.fetch_routes", boom)
    response = Client().post(
        "/api/plan",
        data={
            "origin": "Dallas",
            "destination": "Chicago",
            "departure": "2026-10-13T12:00:00Z",
            "weight_lb": 1000,
            "spacing_miles": 25,
        },
        content_type="application/json",
    )
    assert response.status_code == 502
    assert response.json()["error"] == "insufficient_routes"


def test_invalid_spacing(settings):
    settings.GRAPHHOPPER_API_KEY = "test-key"
    response = Client().post(
        "/api/plan",
        data={"origin": "Dallas", "destination": "Chicago", "departure": "2026-10-13T12:00:00Z", "weight_lb": 1, "spacing_miles": 15},
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_input"
