from datetime import datetime, timedelta, timezone

from planner.checkpoints import checkpoints


def _line():
    # About 69 miles north per degree of latitude.
    return [[-97.0, 32.0], [-97.0, 33.0]]


def test_checkpoint_spacing():
    departure = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    for spacing in (10, 25, 50):
        points = checkpoints(_line(), spacing, departure, duration_seconds=3600)
        assert points[0]["distance_miles"] == 0
        assert points[-1]["lat"] == 33.0
        gaps = [
            points[i + 1]["distance_miles"] - points[i]["distance_miles"]
            for i in range(len(points) - 1)
        ]
        assert all(gap <= spacing + 0.05 for gap in gaps)
        assert any(abs(gap - spacing) < 0.05 for gap in gaps[:-1])


def test_eta_uses_duration_fraction():
    departure = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    points = checkpoints(_line(), 50, departure, duration_seconds=7200)
    midpoint = min(points, key=lambda p: abs(p["distance_miles"] - points[-1]["distance_miles"] / 2))
    expected = departure + timedelta(seconds=7200 * midpoint["distance_miles"] / points[-1]["distance_miles"])
    assert abs((midpoint["eta"] - expected).total_seconds()) < 1
    assert points[-1]["eta"] == departure + timedelta(seconds=7200)
