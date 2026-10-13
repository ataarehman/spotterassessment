import pytest

from planner.risk import (
    RISK_SCORE,
    apply_load,
    classify_rain,
    classify_snow,
    classify_wind,
    combine,
)


def test_wind_band_edges():
    assert classify_wind(0) == "Low"
    assert classify_wind(24.9) == "Low"
    assert classify_wind(25) == "Moderate"
    assert classify_wind(34) == "Moderate"
    assert classify_wind(35) == "High"
    assert classify_wind(44) == "High"
    assert classify_wind(45) == "Severe"
    assert classify_wind(54) == "Severe"
    assert classify_wind(55) == "No Travel"


def test_rain_band_edges():
    assert classify_rain(0) == "Low"
    assert classify_rain(0.09) == "Low"
    assert classify_rain(0.10) == "Moderate"
    assert classify_rain(0.24) == "Moderate"
    assert classify_rain(0.25) == "High"
    assert classify_rain(0.49) == "High"
    assert classify_rain(0.50) == "Severe"
    assert classify_rain(0.99) == "Severe"
    assert classify_rain(1.00) == "Severe"
    assert classify_rain(1.01) == "No Travel"


def test_snow_band_edges():
    assert classify_snow(0) == "Low"
    assert classify_snow(0.49) == "Low"
    assert classify_snow(0.5) == "Moderate"
    assert classify_snow(0.99) == "Moderate"
    assert classify_snow(1.0) == "High"
    assert classify_snow(1.99) == "High"
    assert classify_snow(2.0) == "Severe"
    assert classify_snow(2.99) == "Severe"
    assert classify_snow(3.0) == "Severe"
    assert classify_snow(3.01) == "No Travel"


@pytest.mark.parametrize("weight_lb", [0, 15000, 30000, 45000, 80000])
def test_wind_55_any_load(weight_lb):
    wind_class = classify_wind(60)
    assert apply_load(wind_class, 55, weight_lb) == "No Travel"
    assert apply_load(wind_class, 70, weight_lb) == "No Travel"


def test_load_45_boundary():
    wind_class = classify_wind(50)
    assert wind_class == "Severe"
    assert apply_load(wind_class, 50, 30000) == "Severe"
    assert apply_load(wind_class, 50, 30001) == "No Travel"
    assert apply_load(wind_class, 45, 30000) == "Severe"
    assert apply_load(wind_class, 45, 40000) == "No Travel"
    assert apply_load(wind_class, 54, 35000) == "No Travel"


def test_load_35_boundary():
    wind_class = classify_wind(40)
    assert wind_class == "High"
    assert apply_load(wind_class, 40, 40000) == "High"
    assert apply_load(wind_class, 40, 40001) == "Severe"
    assert apply_load(wind_class, 35, 40000) == "High"
    assert apply_load(wind_class, 35, 50000) == "Severe"
    assert apply_load(wind_class, 44, 45000) == "Severe"


def test_worst_hazard_wins():
    assert combine("Low", "Low", "Low") == "Low"
    assert combine("Moderate", "Low", "Low") == "Moderate"
    assert combine("High", "Moderate", "Low") == "High"
    assert combine("Severe", "High", "Moderate") == "Severe"
    assert combine("No Travel", "Severe", "High") == "No Travel"
    assert RISK_SCORE["Low"] == 1
    assert RISK_SCORE["Moderate"] == 2
    assert RISK_SCORE["High"] == 3
    assert RISK_SCORE["Severe"] == 4
    assert RISK_SCORE["No Travel"] == 5


def test_load_does_not_lower_precip():
    rain = classify_rain(0.60)
    snow = classify_snow(2.5)
    assert rain == "Severe"
    assert snow == "Severe"
    wind_class = classify_wind(40)
    adjusted_wind = apply_load(wind_class, 40, 10000)
    assert adjusted_wind == "High"
    assert combine(adjusted_wind, rain, snow) == "Severe"
