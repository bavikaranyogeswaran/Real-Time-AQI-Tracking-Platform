"""Integration sanity-check — verifies the test app starts and /health responds.

Requires asyncpg + a live PostgreSQL instance (port 5434).
Run inside the Docker container:

    docker exec aqi_backend python -m pytest tests/ -v
"""
import pytest

pytest.importorskip(
    "asyncpg",
    reason="asyncpg not installed — run inside Docker: docker exec aqi_backend python -m pytest tests/",
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
