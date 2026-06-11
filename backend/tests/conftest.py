"""Shared pytest configuration.

Mocks heavy optional dependencies (asyncpg, sklearn, xgboost) and
app.database at import time so the unit-test suite runs without a live
Postgres connection or ML libraries installed.

The stubs must be registered in sys.modules BEFORE pytest collects any
test module; conftest.py at the tests-root is loaded first.
"""
import os
import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Minimal environment so pydantic-settings doesn't raise ValidationError
# ---------------------------------------------------------------------------
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("OPENWEATHER_API_KEY", "test_key")

# ---------------------------------------------------------------------------
# Stub: sklearn (not installed in the host dev environment)
# ---------------------------------------------------------------------------
_sklearn = MagicMock()
_sklearn.ensemble = MagicMock()
_sklearn.ensemble.IsolationForest = MagicMock
sys.modules.setdefault("sklearn", _sklearn)
sys.modules.setdefault("sklearn.ensemble", _sklearn.ensemble)

# ---------------------------------------------------------------------------
# Stub: xgboost (not installed in the host dev environment)
# ---------------------------------------------------------------------------
_xgboost = MagicMock()
_xgboost.XGBRegressor = MagicMock
sys.modules.setdefault("xgboost", _xgboost)

# ---------------------------------------------------------------------------
# Stub: app.database — prevents SQLAlchemy from calling create_async_engine
# (which would import asyncpg) at module import time.
# ---------------------------------------------------------------------------
from sqlalchemy.orm import DeclarativeBase  # noqa: E402


class _TestBase(DeclarativeBase):
    pass


_db = MagicMock()
_db.Base = _TestBase
_db.get_db = MagicMock()
_db.AsyncSessionLocal = MagicMock()
sys.modules["app.database"] = _db
