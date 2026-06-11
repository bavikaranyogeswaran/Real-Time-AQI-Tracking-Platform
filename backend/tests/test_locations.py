"""Integration tests for GET /api/locations.

Requires asyncpg + a live PostgreSQL instance (port 5434).
Run inside the Docker container:

    docker exec aqi_backend python -m pytest tests/test_locations.py -v
"""

import pytest

pytest.importorskip(
    "asyncpg",
    reason="asyncpg not installed — run inside Docker: docker exec aqi_backend python -m pytest tests/",
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_get_locations_returns_200(client):
    r = await client.get("/api/locations")
    assert r.status_code == 200


async def test_get_locations_returns_list(client):
    r = await client.get("/api/locations")
    assert isinstance(r.json(), list)


async def test_get_locations_includes_testville(client, test_data):
    r = await client.get("/api/locations")
    cities = [loc["city"] for loc in r.json()]
    assert test_data["city"] in cities


async def test_get_locations_expected_fields(client, test_data):
    r = await client.get("/api/locations")
    loc = next(loc for loc in r.json() if loc["city"] == test_data["city"])
    for field in ("location_id", "city", "country", "latitude", "longitude"):
        assert field in loc
