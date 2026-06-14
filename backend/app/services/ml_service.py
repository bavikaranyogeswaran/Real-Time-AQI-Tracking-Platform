import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.anomaly import detect_anomaly
from app.ml.features import build_feature_df
from app.ml.forecasting import predict_next_nh
from app.models.air_quality import AirQualityReading
from app.models.location import Location
from app.models.prediction import AQIPrediction
from app.services import bigquery_client as bq

logger = logging.getLogger(__name__)

_FORECAST_LOOKBACK_DAYS = 7


async def run_forecast_for_location(session: AsyncSession, location: Location) -> int:
    """Generate a fresh 7-day (168-hour) forecast for the given location.

    Deletes any existing predictions for the location, fetches the last
    FORECAST_LOOKBACK_DAYS of readings to build features, runs the model,
    and bulk-inserts 168 new AQIPrediction rows.

    Returns the number of predictions inserted (0 if skipped).
    """
    cutoff = datetime.now(UTC) - timedelta(days=_FORECAST_LOOKBACK_DAYS)
    readings = (
        (
            await session.execute(
                select(AirQualityReading)
                .where(
                    AirQualityReading.location_id == location.location_id,
                    AirQualityReading.timestamp >= cutoff,
                )
                .order_by(AirQualityReading.timestamp.asc())
            )
        )
        .scalars()
        .all()
    )

    if len(readings) < 5:
        logger.debug("Skipping forecast for %s — only %d readings.", location.city, len(readings))
        return 0

    df = build_feature_df(readings)
    if df.empty:
        logger.debug("Skipping forecast for %s — empty feature DataFrame.", location.city)
        return 0

    try:
        predictions = predict_next_nh(location.location_id, df, hours=168)
    except FileNotFoundError:
        logger.debug("No forecast model for %s yet — skipping.", location.city)
        return 0
    except Exception as exc:
        logger.warning("Forecast failed for %s: %s", location.city, exc)
        return 0

    # Replace only future predictions so past predictions accumulate for accuracy evaluation
    await session.execute(
        delete(AQIPrediction).where(
            AQIPrediction.location_id == location.location_id,
            AQIPrediction.forecast_for > datetime.now(UTC),
        )
    )

    now = datetime.now(UTC)
    new_preds: list[AQIPrediction] = []
    for p in predictions:
        pred = AQIPrediction(
            prediction_id=str(uuid.uuid4()),
            location_id=location.location_id,
            prediction_time=now,
            forecast_for=p["forecast_for"],
            predicted_aqi=p["predicted_aqi"],
            model_name="xgboost",
        )
        session.add(pred)
        new_preds.append(pred)

    await session.commit()
    logger.info("Inserted %d forecast rows for %s.", len(new_preds), location.city)

    if bq.is_enabled():
        rows = [
            {
                "prediction_id": pred.prediction_id,
                "location_id": pred.location_id,
                "city": location.city,
                "country": location.country,
                "prediction_time": pred.prediction_time.isoformat(),
                "forecast_for": pred.forecast_for.isoformat(),
                "predicted_aqi": float(pred.predicted_aqi),
                "model_name": pred.model_name,
            }
            for pred in new_preds
        ]
        asyncio.create_task(bq.stream_predictions_rows(rows))

    return len(new_preds)


def check_anomaly_for_reading(location_id: str, reading: AirQualityReading) -> bool:
    """Return True if the reading is flagged as anomalous. Never raises."""
    try:
        return detect_anomaly(location_id, reading)
    except Exception as exc:
        logger.debug("Anomaly check failed for %s: %s", location_id, exc)
        return False
