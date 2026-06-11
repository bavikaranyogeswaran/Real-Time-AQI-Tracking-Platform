"""Unit tests for ingestion.py pure functions.

No database or external HTTP calls are made here.
"""

import pytest

from app.services.ingestion import calculate_aqi_from_pm25, get_aqi_category, validate_reading

# ---------------------------------------------------------------------------
# calculate_aqi_from_pm25
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "pm25, expected_aqi",
    [
        (0.0, 0),
        (6.0, 25),  # midpoint of Good band
        (12.0, 50),  # top of Good band
        (12.1, 51),  # bottom of Moderate
        (23.75, 76),  # midpoint of Moderate (75.5 → rounds to 76 via banker's rounding)
        (35.4, 100),  # top of Moderate
        (35.5, 101),  # bottom of USG
        (55.4, 150),  # top of USG
        (55.5, 151),  # bottom of Unhealthy
        (150.4, 200),  # top of Unhealthy
        (150.5, 201),  # bottom of Very Unhealthy
        (250.4, 300),  # top of Very Unhealthy
        (250.5, 301),  # bottom of Hazardous-1
        (350.4, 400),  # top of Hazardous-1
        (350.5, 401),  # bottom of Hazardous-2
        (500.4, 500),  # top of scale
        (600.0, 500),  # above scale → clamped to 500
    ],
)
def test_calculate_aqi_from_pm25_breakpoints(pm25, expected_aqi):
    assert calculate_aqi_from_pm25(pm25) == expected_aqi


def test_calculate_aqi_from_pm25_negative_returns_zero():
    # Negative PM2.5 is below the first breakpoint: returns 0
    assert calculate_aqi_from_pm25(-1.0) == 0


def test_calculate_aqi_from_pm25_linear_interpolation():
    # At the exact midpoint of the Good band (0–12 μg → AQI 0–50)
    # pm25=6 should give AQI 25
    result = calculate_aqi_from_pm25(6.0)
    assert result == 25


# ---------------------------------------------------------------------------
# get_aqi_category
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "aqi, category",
    [
        (0, "Good"),
        (50, "Good"),
        (51, "Moderate"),
        (100, "Moderate"),
        (101, "Unhealthy for Sensitive Groups"),
        (150, "Unhealthy for Sensitive Groups"),
        (151, "Unhealthy"),
        (200, "Unhealthy"),
        (201, "Very Unhealthy"),
        (300, "Very Unhealthy"),
        (301, "Hazardous"),
        (500, "Hazardous"),
        (999, "Hazardous"),
    ],
)
def test_get_aqi_category(aqi, category):
    assert get_aqi_category(aqi) == category


# ---------------------------------------------------------------------------
# validate_reading
# ---------------------------------------------------------------------------


def _make_response(pm25=10.0, extra_components=None):
    """Helper: build a minimal OpenWeather-style response dict."""
    components = {"pm2_5": pm25, "pm10": 20.0, "co": 200.0, "no2": 5.0, "so2": 2.0, "o3": 50.0}
    if extra_components:
        components.update(extra_components)
    return {"list": [{"dt": 1700000000, "components": components}]}


def test_validate_reading_valid():
    assert validate_reading(_make_response(pm25=10.0)) is True


def test_validate_reading_missing_pm25():
    data = {"list": [{"dt": 1700000000, "components": {"pm10": 20.0}}]}
    assert validate_reading(data) is False


def test_validate_reading_negative_pm25():
    assert validate_reading(_make_response(pm25=-1.0)) is False


def test_validate_reading_pm25_above_max():
    assert validate_reading(_make_response(pm25=501.0)) is False


def test_validate_reading_negative_secondary_pollutant():
    assert validate_reading(_make_response(extra_components={"no2": -0.1})) is False


def test_validate_reading_missing_list_key():
    assert validate_reading({}) is False


def test_validate_reading_empty_list():
    assert validate_reading({"list": []}) is False


def test_validate_reading_zero_pm25():
    # pm25=0 is valid (AQI=0)
    assert validate_reading(_make_response(pm25=0.0)) is True


def test_validate_reading_optional_pollutants_can_be_absent():
    # A response with only pm2_5 and no other pollutants is still valid
    data = {"list": [{"dt": 1700000000, "components": {"pm2_5": 5.0}}]}
    assert validate_reading(data) is True
