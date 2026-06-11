"""Shared pytest configuration.

Sets DATABASE_URL to a dummy value so pydantic-settings doesn't error
when importing app modules that reference settings at import time.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("OPENWEATHER_API_KEY", "test_key")
