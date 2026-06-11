"""Integration tests for alert endpoints.

Covers: POST /api/alerts/rules (201), GET /api/alerts (200), PATCH resolve (200).

Requires asyncpg + a live PostgreSQL instance (port 5434).
Run inside the Docker container:

    docker exec aqi_backend python -m pytest tests/test_alerts.py -v
"""

import pytest

pytest.importorskip(
    "asyncpg",
    reason="asyncpg not installed — run inside Docker: docker exec aqi_backend python -m pytest tests/",
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_get_alerts_returns_200(client):
    r = await client.get("/api/alerts")
    assert r.status_code == 200


async def test_get_alerts_returns_list(client):
    r = await client.get("/api/alerts")
    assert isinstance(r.json(), list)


async def test_get_alerts_includes_test_alert(client, test_data):
    # Must run before test_patch_alert_resolve resolves it.
    r = await client.get("/api/alerts")
    ids = [a["alert_id"] for a in r.json()]
    assert test_data["alert_id"] in ids


async def test_post_alert_rule_returns_201(client, test_data):
    payload = {
        "location_id": test_data["location_id"],
        "alert_type": "test_rule",
        "threshold_value": 999,
    }
    r = await client.post("/api/alerts/rules", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["alert_type"] == "test_rule"
    assert body["threshold_value"] == 999


async def test_patch_alert_resolve_returns_200(client, test_data):
    r = await client.patch(f"/api/alerts/{test_data['alert_id']}/resolve")
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"
