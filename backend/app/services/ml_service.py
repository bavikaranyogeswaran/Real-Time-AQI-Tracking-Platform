import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.anomaly import detect_anomaly
from app.ml.features import build_feature_df
from app.ml.forecasting import predict_next_24h
from app.models.air_quality import AirQualityReading
from app.models.location import Location
from app.models.prediction import AQIPrediction

logger = logging.getLogger(__name__)

_FORECAST_LOOKBACK_DAYS = 7


async def run_forecast_for_location(session: AsyncSession, location: Location) -> int:
    """Generate a fresh 24-hour forecast for the given location.

    Deletes any existing predictions for the location, fetches the last
    FORECAST_LOOKBACK_DAYS of readings to build features, runs the model,
    and bulk-inserts 24 new AQIPrediction rows.

    Returns the number of predictions inserted (0 if skipped).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_FORECAST_LOOKBACK_DAYS)
    readings = (
        await session.execute(
            select(AirQualityReading)
            .where(
                AirQualityReading.location_id == location.location_id,
                AirQualityReading.timestamp >= cutoff,
            )
            .order_by(AirQualityReading.timestamp.asc())
        )
    ).scalars().all()

    if len(readings) < 5:
        logger.debug("Skipping forecast for %s — only %d readings.", location.city, len(readings))
        return 0

    df = build_feature_df(readings)
    if df.empty:
        logger.debug("Skipping forecast for %s — empty feature DataFrame.", location.city)
        return 0

    try:
        predictions = predict_next_24h(location.location_id, df)
    except FileNotFoundError:
        logger.debug("No forecast model for %s yet — skipping.", location.city)
        return 0
    except Exception as exc:
        logger.warning("Forecast failed for %s: %s", location.city, exc)
        return 0

    # Replace stale predictions atomically
    await session.execute(
        delete(AQIPrediction).where(AQIPrediction.location_id == location.location_id)
    )

    now = datetime.now(timezone.utc)
    for p in predictions:
        session.add(
            AQIPrediction(
                prediction_id=str(uuid.uuid4()),
                location_id=location.location_id,
                prediction_time=now,
                forecast_for=p["forecast_for"],
                predicted_aqi=p["predicted_aqi"],
                model_name="xgboost",
            )
        )

    await session.commit()
    logger.info("Inserted %d forecast rows for %s.", len(predictions), location.city)
    return len(predictions)


def check_anomaly_for_reading(location_id: str, reading: AirQualityReading) -> bool:
    """Return True if the reading is flagged as anomalous. Never raises."""
    try:
        return detect_anomaly(location_id, reading)
    except Exception as exc:
        logger.debug("Anomaly check failed for %s: %s", location_id, exc)
        return False
