"""Segment risk miles and the assessment's route order."""

from planner.risk import RISK_SCORE


def summarize(stops):
    """stops: dicts with distance_miles and risk (or None when weather is missing)."""
    severe = high = no_travel = 0.0
    weighted = 0.0
    known_miles = 0.0
    unknown = False
    for left, right in zip(stops, stops[1:]):
        miles = right["distance_miles"] - left["distance_miles"]
        if left.get("risk") is None or right.get("risk") is None:
            unknown = True
            continue
        risk = left["risk"] if RISK_SCORE[left["risk"]] >= RISK_SCORE[right["risk"]] else right["risk"]
        if risk == "Severe":
            severe += miles
        elif risk == "High":
            high += miles
        elif risk == "No Travel":
            no_travel += miles
        weighted += miles * RISK_SCORE[risk]
        known_miles += miles
    average = None if known_miles == 0 else weighted / known_miles
    return {
        "severe_miles": severe,
        "high_miles": high,
        "no_travel_miles": no_travel,
        "average_risk": average,
        "unknown": unknown,
    }


def rank(routes):
    def key(item):
        index, route = item
        summary = route["summary"]
        return (
            summary["unknown"],
            summary["no_travel_miles"] > 0,
            summary["no_travel_miles"],
            summary["severe_miles"],
            summary["high_miles"],
            summary["average_risk"] if summary["average_risk"] is not None else float("inf"),
            route["duration_seconds"],
            index,
        )

    ordered = [route for _, route in sorted(enumerate(routes), key=key)]
    eligible = [route for route in ordered if not route["summary"]["unknown"]]
    return ordered, (eligible[0]["id"] if eligible else None)
