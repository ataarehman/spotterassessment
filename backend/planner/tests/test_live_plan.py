import os

import pytest

from planner.services import build_plan


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_PLAN") != "1" or not os.environ.get("GRAPHHOPPER_API_KEY"),
    reason="set RUN_LIVE_PLAN=1 and GRAPHHOPPER_API_KEY to call live providers",
)


def test_live_dallas_chicago():
    plan = build_plan(
        {
            "origin": "Dallas",
            "destination": "Chicago",
            "departure": "2026-10-14T12:00:00Z",
            "weight_lb": 42000,
            "spacing_miles": 50,
        }
    )
    assert plan["profile"] in ("car", "bike", "foot", "truck")
    assert len(plan["routes"]) == 3
    geometries = [tuple(tuple(pair) for pair in route["geometry"]["coordinates"]) for route in plan["routes"]]
    assert len(set(geometries)) == 3
    assert plan["recommended_route_id"] == plan["routes"][0]["id"]
    assert len(plan["heatmap"][0]["hours"]) == 49
    assert all(hour is not None for point in plan["heatmap"] for hour in point["hours"])
    assert plan["routes"][0]["checkpoints"][0]["weather"]["wind_mph"] is not None
