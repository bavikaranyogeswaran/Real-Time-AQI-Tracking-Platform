"""Standalone training script for forecast and anomaly models.

Usage:
    python -m app.ml.train
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.ml.anomaly import _model_path as anomaly_path
from app.ml.anomaly import train_anomaly_model
from app.ml.features import build_feature_df
from app.ml.forecasting import _model_path as forecast_path
from app.ml.forecasting import train_model
from app.models.air_quality import AirQualityReading
from app.models.location import Location

logger = logging.getLogger(__name__)

_LOOKBACK_DAYS = 30


async def train_all() -> None:
    async with AsyncSessionLocal() as session:
        locations = (
            (await session.execute(select(Location).order_by(Location.city))).scalars().all()
        )

        logger.info(
            "Training models for %d locations — lookback %d days", len(locations), _LOOKBACK_DAYS
        )
        cutoff = datetime.now(UTC) - timedelta(days=_LOOKBACK_DAYS)

        for loc in locations:
            readings = (
                (
                    await session.execute(
                        select(AirQualityReading)
                        .where(
                            AirQualityReading.location_id == loc.location_id,
                            AirQualityReading.timestamp >= cutoff,
                        )
                        .order_by(AirQualityReading.timestamp.asc())
                    )
                )
                .scalars()
                .all()
            )

            if len(readings) < 10:
                logger.info("Skipped %s — too few readings (%d)", loc.city, len(readings))
                continue

            df = build_feature_df(readings)

            if df.empty or len(df) < 5:
                logger.info(
                    "Skipped %s — insufficient features after lag fill (df=%d rows)",
                    loc.city,
                    len(df),
                )
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

            logger.info(
                "Trained %s — forecast=%s anomaly=%s rows=%d", loc.city, f_path, a_path, len(df)
            )

        logger.info("Training complete.")


if __name__ == "__main__":
    asyncio.run(train_all())
