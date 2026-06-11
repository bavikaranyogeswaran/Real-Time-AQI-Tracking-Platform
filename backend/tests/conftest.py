"""Shared pytest configuration.

Unit tests run on any machine — no database or ML libraries required.
Integration tests (test_api.py) need asyncpg + PostgreSQL; they skip
automatically when asyncpg is not importable.

This conftest installs stubs for heavy deps ONLY when they are absent,
so the same conftest works both locally and inside the Docker container.
"""
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://aqi_user:aqi_pass@localhost:5434/aqi_db")
os.environ.setdefault("OPENWEATHER_API_KEY", "test_key")

# ------------------------------------------------------------------
# Stub heavy deps that are missing in local dev but present in Docker.
# Stubs are registered before pytest collects any test module.
# ------------------------------------------------------------------
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
    # asyncpg is present → app.database can create a real engine; no stub needed.
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
