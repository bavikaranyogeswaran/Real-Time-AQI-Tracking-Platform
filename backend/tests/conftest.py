"""Shared pytest configuration and integration fixtures.

Unit tests (test_ingestion.py, test_features.py) run on any machine with no
database or ML libraries required.

Integration tests (test_locations.py, test_aqi.py, test_alerts.py,
test_analytics.py) need asyncpg + a live PostgreSQL instance on port 5434.
They skip automatically when asyncpg is not importable.
"""

import os
import sys
from datetime import UTC
from unittest.mock import MagicMock

os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://aqi_user:aqi_pass@localhost:5434/aqi_db"
)
os.environ.setdefault("OPENWEATHER_API_KEY", "test_key")


# ---------------------------------------------------------------------------
# Stub heavy deps that are missing in local dev but present in Docker.
# Stubs are registered before pytest collects any test module.
# ---------------------------------------------------------------------------
def _mock(name: str, **attrs):
    m = MagicMock()
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules.setdefault(name, m)
    return m


try:
    import sklearn  # noqa: F401
except ImportError:
    _sk = _mock("sklearn")
    _sk_ens = _mock("sklearn.ensemble", IsolationForest=MagicMock)
    _sk.ensemble = _sk_ens

try:
    import xgboost  # noqa: F401
except ImportError:
    _mock("xgboost", XGBRegressor=MagicMock)

try:
    import asyncpg  # noqa: F401

    _ASYNCPG_AVAILABLE = True
except ImportError:
    # asyncpg absent → stub the whole database module so SQLAlchemy never tries
    # to import asyncpg at module-load time.  Unit tests don't touch the DB at
    # all, and integration tests skip themselves via pytest.importorskip.
    from sqlalchemy.orm import DeclarativeBase

    class _TestBase(DeclarativeBase):
        pass

    _db = MagicMock()
    _db.Base = _TestBase
    _db.get_db = MagicMock()
    _db.AsyncSessionLocal = MagicMock()
    sys.modules["app.database"] = _db
    _ASYNCPG_AVAILABLE = False

# ---------------------------------------------------------------------------
# Integration fixtures — only registered when asyncpg is available so
# unit-only environments can still collect and run test_ingestion + test_features.
# ---------------------------------------------------------------------------
if _ASYNCPG_AVAILABLE:
    import uuid
    from datetime import datetime, timedelta

    import pytest_asyncio
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from app.api import alerts as alerts_mod
    from app.api import analytics as analytics_mod
    from app.api import aqi as aqi_mod
    from app.api import locations as locations_mod
    from app.config import settings
    from app.database import get_db
    from app.models.air_quality import AirQualityReading
    from app.models.alert import Alert
    from app.models.location import Location

    # Minimal FastAPI app: all routers, no scheduler or seed lifespan.
    _app = FastAPI(title="AQI Test")
    _app.include_router(locations_mod.router, prefix="/api")
    _app.include_router(aqi_mod.router, prefix="/api")
    _app.include_router(alerts_mod.router, prefix="/api")
    _app.include_router(analytics_mod.router, prefix="/api")

    @_app.get("/health")
    async def _health():
        return {"status": "ok"}

    @pytest_asyncio.fixture(scope="session")
    async def engine():
        e = create_async_engine(settings.database_url, echo=False)
        yield e
        await e.dispose()

    @pytest_asyncio.fixture(scope="session")
    async def test_data(engine):
        """Insert one Location + 5 Readings + 1 Alert; delete everything after the session."""
        loc_id = f"test-{uuid.uuid4()}"
        alert_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with SessionLocal() as session:
            session.add(
                Location(
                    location_id=loc_id,
                    city="Testville",
                    country="Testland",
                    latitude=1.23,
                    longitude=4.56,
                    source="test",
                )
            )
            await session.flush()  # ensure FK target exists before readings/alerts
            for i in range(5):
                session.add(
                    AirQualityReading(
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
                    )
                )
            session.add(
                Alert(
                    alert_id=alert_id,
                    location_id=loc_id,
                    alert_type="unhealthy",
                    threshold_value=150,
                    actual_aqi=180,
                    status="active",
                    created_at=now,
                )
            )
            await session.commit()

        yield {"location_id": loc_id, "city": "Testville", "alert_id": alert_id}

        from app.models.alert_rule import (
            AlertRule,  # imported late to avoid circular at module load
        )

        async with SessionLocal() as session:
            await session.execute(delete(AlertRule).where(AlertRule.location_id == loc_id))
            await session.execute(delete(Alert).where(Alert.location_id == loc_id))
            await session.execute(
                delete(AirQualityReading).where(AirQualityReading.location_id == loc_id)
            )
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
