"""Integration tests for all FastAPI routes.

Requires asyncpg + a live PostgreSQL instance (port 5434).
Run inside the Docker container:

    docker exec aqi_backend python -m pytest tests/test_api.py -v

Tests skip automatically when asyncpg is not installed.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

# Must be the first pytest call — halts collection immediately if asyncpg is absent,
# preventing any subsequent import (pytest_asyncio, SQLAlchemy dialects, etc.) from
# running in environments that don't have the full backend stack installed.
pytest.importorskip(
    "asyncpg",
    reason="asyncpg not installed — run inside Docker: docker exec aqi_backend python -m pytest tests/test_api.py",
)

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from sqlalchemy import delete  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

from app.api import alerts as alerts_mod  # noqa: E402
from app.api import analytics as analytics_mod  # noqa: E402
from app.api import aqi as aqi_mod  # noqa: E402
from app.api import locations as locations_mod  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import get_db  # noqa: E402
from app.models.air_quality import AirQualityReading  # noqa: E402
from app.models.alert import Alert  # noqa: E402
from app.models.location import Location  # noqa: E402

# ---------------------------------------------------------------------------
# Test app — same routers as production but no scheduler or seed lifespan.
# ---------------------------------------------------------------------------
_app = FastAPI(title="AQI Test")
_app.include_router(locations_mod.router, prefix="/api")
_app.include_router(aqi_mod.router,       prefix="/api")
_app.include_router(alerts_mod.router,    prefix="/api")
_app.include_router(analytics_mod.router, prefix="/api")


@_app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Session-scoped fixtures — DB engine, test data, HTTP client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def engine():
    e = create_async_engine(settings.database_url, echo=False)
    yield e
    await e.dispose()


@pytest_asyncio.fixture(scope="session")
async def test_data(engine):
    """Insert one location + 5 readings + 1 alert; delete them after the session."""
    loc_id = f"test-{uuid.uuid4()}"
    alert_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with SessionLocal() as session:
        session.add(Location(
            location_id=loc_id,
            city="Testville",
            country="Testland",
            latitude=1.23,
            longitude=4.56,
            source="test",
        ))
        for i in range(5):
            session.add(AirQualityReading(
                reading_id=str(uuid.uuid4()),
                location_id=loc_id,
                timestamp=now - timedelta(hours=i),
                aqi=85 + i,
                pm25=10.0 + i,
                pm10=20.0,
                co=200.0,
                no2=5.0,
                so2=2.0,
                o3=50.0,
                data_source="test",
            ))
        session.add(Alert(
            alert_id=alert_id,
            location_id=loc_id,
            alert_type="unhealthy",
            threshold_value=150,
            actual_aqi=180,
            status="active",
            created_at=now,
        ))
        await session.commit()

    yield {"location_id": loc_id, "city": "Testville", "alert_id": alert_id}

    from app.models.alert_rule import AlertRule

    async with SessionLocal() as session:
        await session.execute(delete(AlertRule).where(AlertRule.location_id == loc_id))
        await session.execute(delete(Alert).where(Alert.location_id == loc_id))
        await session.execute(delete(AirQualityReading).where(AirQualityReading.location_id == loc_id))
        await session.execute(delete(Location).where(Location.location_id == loc_id))
        await session.commit()


@pytest_asyncio.fixture(scope="session")
async def client(engine, test_data):
    """In-process ASGI client with get_db overridden to use the test engine."""
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with SessionLocal() as session:
            yield session

    _app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as ac:
        yield ac
    _app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

async def test_get_locations_returns_list(client):
    r = await client.get("/api/locations")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_get_locations_includes_test_location(client, test_data):
    r = await client.get("/api/locations")
    cities = [loc["city"] for loc in r.json()]
    assert test_data["city"] in cities


# ---------------------------------------------------------------------------
# AQI current
# ---------------------------------------------------------------------------

async def test_get_current_aqi_valid_city(client, test_data):
    r = await client.get("/api/aqi/current", params={"city": test_data["city"]})
    assert r.status_code == 200
    body = r.json()
    assert body["city"] == test_data["city"]
    assert isinstance(body["aqi"], int)
    assert "category" in body


async def test_get_current_aqi_unknown_city_returns_404(client):
    r = await client.get("/api/aqi/current", params={"city": "NoSuchCityXYZ"})
    assert r.status_code == 404


async def test_get_current_aqi_case_insensitive(client, test_data):
    # ilike should match lowercase version of the city name
    r = await client.get("/api/aqi/current", params={"city": test_data["city"].lower()})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# AQI history
# ---------------------------------------------------------------------------

async def test_get_history_default_days(client, test_data):
    r = await client.get("/api/aqi/history", params={"city": test_data["city"]})
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 5  # we inserted 5 readings


async def test_get_history_respects_days_param(client, test_data):
    # Our readings are within the last 5 hours; days=1 should include all of them
    r = await client.get("/api/aqi/history", params={"city": test_data["city"], "days": 1})
    assert r.status_code == 200
    assert len(r.json()) == 5


async def test_get_history_days_out_of_range(client, test_data):
    r = await client.get("/api/aqi/history", params={"city": test_data["city"], "days": 0})
    assert r.status_code == 422  # FastAPI query validation


# ---------------------------------------------------------------------------
# Pollutants
# ---------------------------------------------------------------------------

async def test_get_pollutants_valid_city(client, test_data):
    r = await client.get("/api/aqi/pollutants", params={"city": test_data["city"]})
    assert r.status_code == 200
    body = r.json()
    for field in ("pm25", "pm10", "co", "no2", "so2", "o3"):
        assert field in body


# ---------------------------------------------------------------------------
# Forecast (empty list is acceptable — no model trained yet for test data)
# ---------------------------------------------------------------------------

async def test_get_forecast_returns_list(client, test_data):
    r = await client.get("/api/aqi/forecast", params={"city": test_data["city"]})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

async def test_get_alerts_returns_list(client):
    r = await client.get("/api/alerts")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_get_alerts_includes_test_alert(client, test_data):
    r = await client.get("/api/alerts")
    ids = [a["alert_id"] for a in r.json()]
    assert test_data["alert_id"] in ids


async def test_post_alert_rule_creates_rule(client, test_data):
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


async def test_patch_alert_resolve(client, test_data):
    r = await client.patch(f"/api/alerts/{test_data['alert_id']}/resolve")
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

async def test_city_comparison_returns_list(client):
    r = await client.get("/api/analytics/city-comparison")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_city_comparison_includes_test_city(client, test_data):
    r = await client.get("/api/analytics/city-comparison")
    cities = [c["city"] for c in r.json()]
    assert test_data["city"] in cities


async def test_trends_weekly(client, test_data):
    r = await client.get("/api/analytics/trends", params={
        "city": test_data["city"], "period": "weekly",
    })
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_trends_invalid_period(client, test_data):
    r = await client.get("/api/analytics/trends", params={
        "city": test_data["city"], "period": "decadely",
    })
    assert r.status_code == 400


async def test_peak_hours(client, test_data):
    r = await client.get("/api/analytics/peak-hours", params={"city": test_data["city"]})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


async def test_distribution(client, test_data):
    r = await client.get("/api/analytics/distribution", params={"city": test_data["city"]})
    assert r.status_code == 200
    body = r.json()
    # Returns a list of {"category": str, "count": int}
    assert isinstance(body, list)
    assert all("category" in item and "count" in item for item in body)
    # Test readings all have AQI 85-89 → every entry must be "Moderate"
    assert all(item["category"] == "Moderate" for item in body)
