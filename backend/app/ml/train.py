"""Standalone training script for forecast and anomaly models.

Usage:
    python -m app.ml.train
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.ml.anomaly import _model_path as anomaly_path
from app.ml.anomaly import train_anomaly_model
from app.ml.features import build_feature_df
from app.ml.forecasting import _model_path as forecast_path
from app.ml.forecasting import train_model
from app.models.air_quality import AirQualityReading
from app.models.location import Location

_LOOKBACK_DAYS = 30


async def train_all() -> None:
    async with AsyncSessionLocal() as session:
        locations = (await session.execute(select(Location).order_by(Location.city))).scalars().all()

        print(f"\nTraining models for {len(locations)} locations — lookback {_LOOKBACK_DAYS} days\n")
        print(f"{'City':<20} {'Readings':>8}  {'Forecast':>8}  {'Anomaly':>8}  Status")
        print("-" * 72)

        cutoff = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)

        for loc in locations:
            readings = (
                await session.execute(
                    select(AirQualityReading)
                    .where(
                        AirQualityReading.location_id == loc.location_id,
                        AirQualityReading.timestamp >= cutoff,
                    )
                    .order_by(AirQualityReading.timestamp.asc())
                )
            ).scalars().all()

            if len(readings) < 10:
                print(f"{loc.city:<20} {len(readings):>8}  {'—':>8}  {'—':>8}  skipped (too few readings)")
                continue

            df = build_feature_df(readings)

            if df.empty or len(df) < 5:
                print(f"{loc.city:<20} {len(readings):>8}  {'—':>8}  {'—':>8}  skipped (insufficient features after lag fill)")
                continue

            try:
                train_model(loc.location_id, df)
                f_path = forecast_path(loc.location_id).name
            except Exception as exc:
                f_path = f"ERR: {exc}"

            try:
                train_anomaly_model(loc.location_id, df)
                a_path = anomaly_path(loc.location_id).name
            except Exception as exc:
                a_path = f"ERR: {exc}"

            print(f"{loc.city:<20} {len(df):>8}  {f_path:>8}  {a_path:>8}  ok")

        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(train_all())
