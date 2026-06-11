"""Unit tests for ml/features.py — build_feature_df logic.

Uses SimpleNamespace to stand in for AirQualityReading ORM objects so no
database is needed.
"""

from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd
import pytest

from app.ml.features import build_feature_df


def _reading(ts: str, aqi: int, **kwargs) -> SimpleNamespace:
    """Create a lightweight mock AirQualityReading."""
    defaults = {"pm25": 10.0, "pm10": 20.0, "co": 200.0, "no2": 5.0, "so2": 2.0, "o3": 50.0}
    defaults.update(kwargs)
    return SimpleNamespace(
        timestamp=datetime.fromisoformat(ts).replace(tzinfo=UTC),
        aqi=float(aqi),
        **defaults,
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty_df():
    df = build_feature_df([])
    assert df.empty


def test_single_reading_returns_non_empty_df():
    # One reading: lags fall back to the nearest (itself) → should not be dropped
    readings = [_reading("2024-01-01T12:00:00", 80)]
    df = build_feature_df(readings)
    assert len(df) == 1


# ---------------------------------------------------------------------------
# Column contract
# ---------------------------------------------------------------------------

EXPECTED_COLS = {
    "aqi",
    "pm25",
    "pm10",
    "co",
    "no2",
    "so2",
    "o3",
    "aqi_lag_1h",
    "aqi_lag_3h",
    "aqi_lag_24h",
    "hour",
    "day_of_week",
    "month",
    "is_weekend",
}


def _hourly_readings(n: int, base: str = "2024-01-15T00:00:00") -> list:
    """Generate n hourly readings starting from base."""
    base_dt = datetime.fromisoformat(base).replace(tzinfo=UTC)
    return [
        _reading(
            (base_dt + pd.Timedelta(hours=i)).isoformat(),
            aqi=50 + i,
        )
        for i in range(n)
    ]


def test_output_contains_all_expected_columns():
    readings = _hourly_readings(30)
    df = build_feature_df(readings)
    assert not df.empty
    assert EXPECTED_COLS.issubset(set(df.columns))


def test_no_nan_in_output():
    readings = _hourly_readings(30)
    df = build_feature_df(readings)
    assert not df.isnull().any().any()


# ---------------------------------------------------------------------------
# Time features
# ---------------------------------------------------------------------------


def test_is_weekend_flag():
    # 2024-01-13 is Saturday (day_of_week=5 → is_weekend=1)
    # 2024-01-15 is Monday  (day_of_week=0 → is_weekend=0)
    readings = [
        _reading("2024-01-13T10:00:00", 60),
        _reading("2024-01-15T10:00:00", 70),
    ]
    df = build_feature_df(readings)
    saturday_rows = df[df["day_of_week"] == 5]
    monday_rows = df[df["day_of_week"] == 0]
    assert (saturday_rows["is_weekend"] == 1).all()
    assert (monday_rows["is_weekend"] == 0).all()


def test_hour_range():
    readings = _hourly_readings(25)
    df = build_feature_df(readings)
    assert df["hour"].between(0, 23).all()


def test_month_range():
    readings = _hourly_readings(10, base="2024-06-01T00:00:00")
    df = build_feature_df(readings)
    assert df["month"].between(1, 12).all()


# ---------------------------------------------------------------------------
# Lag feature correctness
# ---------------------------------------------------------------------------


def test_lag_1h_matches_previous_reading():
    # With exactly 1-hour gaps the lag_1h should equal the previous row's AQI.
    readings = _hourly_readings(5)
    df = build_feature_df(readings).reset_index(drop=True)
    # Row i: aqi = 50+i; its aqi_lag_1h should match aqi of reading i-1 = 50+(i-1)
    for i in range(1, len(df)):
        assert df.loc[i, "aqi_lag_1h"] == pytest.approx(df.loc[i - 1, "aqi"], abs=1)


def test_lag_values_are_numeric():
    readings = _hourly_readings(30)
    df = build_feature_df(readings)
    for col in ("aqi_lag_1h", "aqi_lag_3h", "aqi_lag_24h"):
        assert pd.api.types.is_numeric_dtype(df[col])


# ---------------------------------------------------------------------------
# Sorting is stable (output sorted by timestamp ascending)
# ---------------------------------------------------------------------------


def test_output_sorted_ascending():
    import random

    readings = _hourly_readings(20)
    random.shuffle(readings)
    df = build_feature_df(readings)
    assert df["aqi"].is_monotonic_increasing or len(df) <= 1
