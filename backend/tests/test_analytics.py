"""Integration tests for analytics endpoints.

Covers: city-comparison, trends (weekly + invalid period), peak-hours, distribution.

Requires asyncpg + a live PostgreSQL instance (port 5434).
Run inside the Docker container:

    docker exec aqi_backend python -m pytest tests/test_analytics.py -v
"""
import pytest

pytest.importorskip(
    "asyncpg",
    reason="asyncpg not installed — run inside Docker: docker exec aqi_backend python -m pytest tests/",
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# /api/analytics/city-comparison
# ---------------------------------------------------------------------------

async def test_city_comparison_returns_200_list(client):
    r = await client.get("/api/analytics/city-comparison")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_city_comparison_includes_test_city(client, test_data):
    r = await client.get("/api/analytics/city-comparison")
    cities = [c["city"] for c in r.json()]
    assert test_data["city"] in cities


# ---------------------------------------------------------------------------
# /api/analytics/trends
# ---------------------------------------------------------------------------

async def test_trends_weekly_returns_200_list(client, test_data):
    r = await client.get("/api/analytics/trends", params={
        "city": test_data["city"], "period": "weekly",
    })
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_trends_invalid_period_returns_400(client, test_data):
    r = await client.get("/api/analytics/trends", params={
        "city": test_data["city"], "period": "decadely",
    })
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# /api/analytics/peak-hours
# ---------------------------------------------------------------------------

async def test_peak_hours_returns_200_list(client, test_data):
    r = await client.get("/api/analytics/peak-hours", params={"city": test_data["city"]})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# /api/analytics/distribution
# ---------------------------------------------------------------------------

async def test_distribution_returns_200_with_expected_shape(client, test_data):
    r = await client.get("/api/analytics/distribution", params={"city": test_data["city"]})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert all("category" in item and "count" in item for item in body)
    # All 5 test readings have AQI 85–89 → every bucket must be "Moderate".
    assert all(item["category"] == "Moderate" for item in body)
