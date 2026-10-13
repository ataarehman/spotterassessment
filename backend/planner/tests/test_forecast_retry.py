from planner.clients import clear_forecast_cache, fetch_forecasts


class Sequence:
    def __init__(self, codes):
        self.codes = list(codes)
        self.calls = 0
        self.slept = []

    def get(self, url, params=None, timeout=None):
        self.calls += 1
        code = self.codes.pop(0)
        return _Response(code)


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code

    def json(self):
        return {
            "hourly_units": {"snowfall": "inch"},
            "hourly": {
                "time": ["2026-10-14T12:00"],
                "wind_speed_10m": [10],
                "precipitation": [0],
                "snowfall": [0],
            },
        }


def test_retries_503_then_uses_real_payload(settings):
    clear_forecast_cache()
    sequence = Sequence([503, 503, 200])
    result = fetch_forecasts(
        [{"lat": 32.78, "lng": -96.8}],
        "2026-10-14T12:00",
        49,
        session=sequence,
        sleeper=sequence.slept.append,
    )
    assert sequence.calls == 3
    assert sequence.slept[0] >= 0.5
    assert sequence.slept[1] >= 1.0
    assert result[0]["2026-10-14T12:00"]["wind_mph"] == 10


def test_does_not_invent_weather_after_exhausted_503(settings):
    clear_forecast_cache()
    sequence = Sequence([503, 429, 503, 503])
    try:
        fetch_forecasts(
            [{"lat": 33.0, "lng": -97.0}],
            "2026-10-14T12:00",
            49,
            session=sequence,
            sleeper=lambda delay: None,
        )
    except Exception as exc:
        assert "503" in str(exc)
    else:
        raise AssertionError("expected provider error")
    assert sequence.calls == 4


def test_cache_avoids_second_fetch_within_ttl(settings):
    clear_forecast_cache()
    first = Sequence([200])
    point = [{"lat": 34.0, "lng": -98.0}]
    fetch_forecasts(point, "2026-10-14T12:00", 49, session=first, sleeper=lambda delay: None, use_cache=True)
    second = Sequence([500])
    again = fetch_forecasts(point, "2026-10-14T12:00", 49, session=second, sleeper=lambda delay: None, use_cache=True)
    assert second.calls == 0
    assert again[0]["2026-10-14T12:00"]["wind_mph"] == 10
    clear_forecast_cache()
