"""Integration tests for AQI endpoints: /current, /history, /pollutants, /forecast.

Requires asyncpg + a live PostgreSQL instance (port 5434).
Run inside the Docker container:

    docker exec aqi_backend python -m pytest tests/test_aqi.py -v
"""

import pytest

pytest.importorskip(
    "asyncpg",
    reason="asyncpg not installed — run inside Docker: docker exec aqi_backend python -m pytest tests/",
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# /api/aqi/current
# ---------------------------------------------------------------------------


async def test_current_valid_city_returns_200(client, test_data):
    r = await client.get("/api/aqi/current", params={"city": test_data["city"]})
    assert r.status_code == 200


async def test_current_response_has_expected_fields(client, test_data):
    r = await client.get("/api/aqi/current", params={"city": test_data["city"]})
    body = r.json()
    assert body["city"] == test_data["city"]
    assert isinstance(body["aqi"], int)
    assert "category" in body


async def test_current_unknown_city_returns_404(client):
    r = await client.get("/api/aqi/current", params={"city": "NoSuchCityXYZ"})
    assert r.status_code == 404


async def test_current_case_insensitive(client, test_data):
    r = await client.get("/api/aqi/current", params={"city": test_data["city"].lower()})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# /api/aqi/history
# ---------------------------------------------------------------------------


async def test_history_returns_200_list(client, test_data):
    r = await client.get("/api/aqi/history", params={"city": test_data["city"]})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_history_default_days_includes_all_readings(client, test_data):
    r = await client.get("/api/aqi/history", params={"city": test_data["city"]})
    assert len(r.json()) == 5  # fixture inserts exactly 5 readings


async def test_history_days_param_respected(client, test_data):
    # All 5 readings are within the last 5 hours; days=1 should still return them all.
    r = await client.get("/api/aqi/history", params={"city": test_data["city"], "days": 1})
    assert r.status_code == 200
    assert len(r.json()) == 5


async def test_history_days_zero_returns_422(client, test_data):
    r = await client.get("/api/aqi/history", params={"city": test_data["city"], "days": 0})
    assert r.status_code == 422  # FastAPI query validation rejects days < 1


# ---------------------------------------------------------------------------
# /api/aqi/pollutants
# ---------------------------------------------------------------------------


async def test_pollutants_returns_200_with_required_fields(client, test_data):
    r = await client.get("/api/aqi/pollutants", params={"city": test_data["city"]})
    assert r.status_code == 200
    body = r.json()
    for field in ("pm25", "pm10", "co", "no2", "so2", "o3"):
        assert field in body


# ---------------------------------------------------------------------------
# /api/aqi/forecast
# ---------------------------------------------------------------------------


async def test_forecast_returns_200_list(client, test_data):
    r = await client.get("/api/aqi/forecast", params={"city": test_data["city"]})
    assert r.status_code == 200
    # Empty list is valid — no model has been trained for the test city.
    assert isinstance(r.json(), list)
