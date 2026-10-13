from planner.ranking import rank, summarize


def _route(route_id, risks, duration):
    stops = []
    for index, risk in enumerate(risks):
        stops.append({"distance_miles": index * 10.0, "risk": risk})
    return {
        "id": route_id,
        "duration_seconds": duration,
        "summary": summarize(stops),
    }


def test_rank_pdf_order():
    severe = _route("severe", ["Severe", "Low"], 100)
    high = _route("high", ["High", "Low"], 100)
    average = _route("average", ["Moderate", "Low"], 100)
    fast = _route("fast", ["Low", "Low"], 50)
    slow = _route("slow", ["Low", "Low"], 90)
    ordered, best = rank([slow, severe, fast, high, average])
    assert [route["id"] for route in ordered] == ["fast", "slow", "average", "high", "severe"]
    assert best == "fast"


def test_no_travel_sorts_last():
    clean = _route("clean", ["High", "High"], 9999)
    blocked = _route("blocked", ["No Travel", "Low"], 10)
    ordered, best = rank([blocked, clean])
    assert [route["id"] for route in ordered] == ["clean", "blocked"]
    assert best == "clean"


def test_missing_forecast_is_not_recommended():
    unknown = _route("unknown", ["Low", None], 10)
    known = _route("known", ["Severe", "Severe"], 10)
    ordered, best = rank([unknown, known])
    assert ordered[0]["id"] == "known"
    assert best == "known"
    assert unknown["summary"]["unknown"] is True
