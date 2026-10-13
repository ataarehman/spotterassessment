"""Weather hazard classification and load-adjusted wind risk."""

RISK_SCORE = {
    "Low": 1,
    "Moderate": 2,
    "High": 3,
    "Severe": 4,
    "No Travel": 5,
}


def classify_wind(mph: float) -> str:
    if mph >= 55:
        return "No Travel"
    if mph >= 45:
        return "Severe"
    if mph >= 35:
        return "High"
    if mph >= 25:
        return "Moderate"
    return "Low"


def classify_rain(inches_per_hour: float) -> str:
    if inches_per_hour > 1.00:
        return "No Travel"
    if inches_per_hour >= 0.50:
        return "Severe"
    if inches_per_hour >= 0.25:
        return "High"
    if inches_per_hour >= 0.10:
        return "Moderate"
    return "Low"


def classify_snow(inches_per_hour: float) -> str:
    if inches_per_hour > 3.0:
        return "No Travel"
    if inches_per_hour >= 2.0:
        return "Severe"
    if inches_per_hour >= 1.0:
        return "High"
    if inches_per_hour >= 0.5:
        return "Moderate"
    return "Low"


def apply_load(wind_class: str, wind_mph: float, weight_lb: float) -> str:
    if wind_mph >= 55:
        return "No Travel"
    # Same spans as the wind table: 45–54 is [45, 55) and 35–44 is [35, 45).
    if 45 <= wind_mph < 55 and weight_lb > 30000:
        return "No Travel"
    if 35 <= wind_mph < 45 and weight_lb > 40000:
        return "Severe"
    return wind_class


def combine(wind_class: str, rain_class: str, snow_class: str) -> str:
    classes = (wind_class, rain_class, snow_class)
    return max(classes, key=lambda c: RISK_SCORE[c])
