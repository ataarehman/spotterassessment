from datetime import datetime, timedelta, timezone

import pytest

from planner.weather import (
    InsufficientRoutes,
    forecast_hours_needed,
    parse_graphhopper_routes,
    sample_at,
    snow_cm_to_inches,
)


def test_sample_hour_containing_eta():
    hourly = {
        "2026-10-13T14:00": {"wind_mph": 10, "rain_in_hr": 0, "snow_in_hr": 0},
        "2026-10-13T15:00": {"wind_mph": 40, "rain_in_hr": 0.2, "snow_in_hr": 0},
    }
    eta = datetime(2026, 10, 13, 14, 20, tzinfo=timezone.utc)
    assert sample_at(hourly, eta)["wind_mph"] == 10


def test_missing_sample_is_unknown():
    hourly = {"2026-10-13T14:00": {"wind_mph": None, "rain_in_hr": 0, "snow_in_hr": 0}}
    eta = datetime(2026, 10, 13, 14, 5, tzinfo=timezone.utc)
    assert sample_at(hourly, eta) is None
    assert sample_at({}, eta) is None


def test_snowfall_cm_converts_to_inches():
    assert snow_cm_to_inches(2.54) == pytest.approx(1.0)
    assert snow_cm_to_inches(None) is None


def test_forecast_covers_arrival_past_48_hours():
    departure = datetime(2026, 10, 13, 0, 30, tzinfo=timezone.utc)
    arrival = departure + timedelta(hours=60, minutes=10)
    assert forecast_hours_needed(departure, arrival) == 61


def test_fewer_than_three_routes_errors():
    payload = {
        "paths": [
            {"distance": 1000, "time": 60000, "points": {"coordinates": [[0, 0], [1, 1]]}},
            {"distance": 1100, "time": 70000, "points": {"coordinates": [[0, 0], [1, 2]]}},
        ]
    }
    with pytest.raises(InsufficientRoutes):
        parse_graphhopper_routes(payload)


def test_graphhopper_keeps_real_coordinates():
    coords = [[[-97, 32], [-96, 33]], [[-97, 32], [-98, 33]], [[-97, 32], [-97, 34]]]
    payload = {
        "paths": [
            {"distance": 1000 * (i + 1), "time": 1000 * (i + 1), "points": {"coordinates": line}}
            for i, line in enumerate(coords)
        ]
    }
    routes = parse_graphhopper_routes(payload)
    assert [route["geometry"] for route in routes] == coords
