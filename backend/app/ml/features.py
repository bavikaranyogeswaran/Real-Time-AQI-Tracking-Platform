from collections.abc import Sequence

import pandas as pd

from app.models.air_quality import AirQualityReading

_LAG_WINDOWS = [
    ("aqi_lag_1h", pd.Timedelta("1h")),
    ("aqi_lag_3h", pd.Timedelta("3h")),
    ("aqi_lag_24h", pd.Timedelta("24h")),
]

# Maximum gap allowed when matching a lag timestamp to an actual reading
_LAG_TOLERANCE = pd.Timedelta("15min")


def build_feature_df(readings: Sequence[AirQualityReading]) -> pd.DataFrame:
    """Build a feature matrix from a list of AirQualityReading ORM objects.

    Features:
      - Pollutants:   pm25, pm10, co, no2, so2, o3
      - Weather:      temperature (°C), humidity (%), wind_speed (m/s)
      - Lag AQI:      aqi_lag_1h, aqi_lag_3h, aqi_lag_24h  (time-based, ±15 min tolerance)
      - Time:         hour, day_of_week, month, is_weekend
    Target: aqi

    Rows with any NaN (e.g. missing lag matches) are dropped.
    """
    if not readings:
        return pd.DataFrame()

    df = pd.DataFrame(
        [
            {
                "timestamp": r.timestamp,
                "aqi": float(r.aqi),
                "pm25": r.pm25 or 0.0,
                "pm10": r.pm10 or 0.0,
                "co": r.co or 0.0,
                "no2": r.no2 or 0.0,
                "so2": r.so2 or 0.0,
                "o3": r.o3 or 0.0,
                "temperature": r.temperature,
                "humidity": r.humidity,
                "wind_speed": r.wind_speed,
            }
            for r in readings
        ]
    )

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Fill missing weather with column median so rows aren't needlessly dropped
    for col in ("temperature", "humidity", "wind_speed"):
        median = df[col].median()
        df[col] = df[col].fillna(median if pd.notna(median) else 0.0)

    # Time features
    df["hour"] = df["timestamp"].dt.hour  # type: ignore
    df["day_of_week"] = df["timestamp"].dt.dayofweek  # type: ignore
    df["month"] = df["timestamp"].dt.month  # type: ignore
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

    # Time-based lag features using merge_asof.
    # First attempt: strict ±15 min tolerance. Any unmatched rows are filled
    # with the nearest available reading (no tolerance) so early-stage DBs
    # with less than 24 h of history still produce usable training rows.
    aqi_lookup = df[["timestamp", "aqi"]].copy()

    for col_name, delta in _LAG_WINDOWS:
        query = pd.DataFrame({"timestamp": df["timestamp"] - delta})
        strict = pd.merge_asof(
            query,
            aqi_lookup.rename(columns={"aqi": col_name}),
            on="timestamp",
            direction="nearest",
            tolerance=_LAG_TOLERANCE,
        )
        fallback = pd.merge_asof(
            query,
            aqi_lookup.rename(columns={"aqi": col_name}),
            on="timestamp",
            direction="nearest",
        )
        col_values = strict[col_name].where(strict[col_name].notna(), fallback[col_name])
        df[col_name] = col_values.values

    df = df.dropna().reset_index(drop=True)
    return df
