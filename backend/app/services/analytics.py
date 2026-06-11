from datetime import UTC, datetime, timedelta

from sqlalchemy import case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.models.air_quality import AirQualityReading
from app.models.location import Location
from app.services.ingestion import get_aqi_category


async def get_daily_averages(session: AsyncSession, location_id: str, days: int) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    date_col = cast(AirQualityReading.timestamp, Date).label("date")
    result = await session.execute(
        select(
            date_col,
            func.avg(AirQualityReading.aqi).label("avg_aqi"),
            func.min(AirQualityReading.aqi).label("min_aqi"),
            func.max(AirQualityReading.aqi).label("max_aqi"),
        )
        .where(
            AirQualityReading.location_id == location_id,
            AirQualityReading.timestamp >= cutoff,
        )
        .group_by(date_col)
        .order_by(date_col.asc())
    )
    return [
        {
            "date": row.date,
            "avg_aqi": round(float(row.avg_aqi), 1),
            "min_aqi": row.min_aqi,
            "max_aqi": row.max_aqi,
        }
        for row in result.all()
    ]


async def get_hourly_averages(session: AsyncSession, location_id: str) -> list[dict]:
    hour_col = func.extract("hour", AirQualityReading.timestamp).label("hour")
    result = await session.execute(
        select(
            hour_col,
            func.avg(AirQualityReading.aqi).label("avg_aqi"),
        )
        .where(AirQualityReading.location_id == location_id)
        .group_by(hour_col)
        .order_by(hour_col.asc())
    )
    return [
        {"hour": int(row.hour), "avg_aqi": round(float(row.avg_aqi), 1)} for row in result.all()
    ]


async def get_aqi_distribution(session: AsyncSession, location_id: str) -> list[dict]:
    category_col = case(
        (AirQualityReading.aqi <= 50, "Good"),
        (AirQualityReading.aqi <= 100, "Moderate"),
        (AirQualityReading.aqi <= 150, "Unhealthy for Sensitive Groups"),
        (AirQualityReading.aqi <= 200, "Unhealthy"),
        (AirQualityReading.aqi <= 300, "Very Unhealthy"),
        else_="Hazardous",
    ).label("category")
    result = await session.execute(
        select(category_col, func.count().label("count"))
        .where(AirQualityReading.location_id == location_id)
        .group_by(category_col)
        .order_by(func.count().desc())
    )
    return [{"category": row.category, "count": row.count} for row in result.all()]


async def get_data_gaps(
    session: AsyncSession,
    location_id: str,
    lookback_hours: int = 24,
    threshold_minutes: int = 20,
) -> list[dict]:
    """Return time intervals within the lookback window where readings are missing.

    A gap is reported when consecutive readings are more than threshold_minutes
    apart (default 20 min = 2× the 10-min poll cycle), or when the most recent
    reading is older than threshold_minutes relative to now.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    now = datetime.now(UTC)

    rows = await session.scalars(
        select(AirQualityReading.timestamp)
        .where(
            AirQualityReading.location_id == location_id,
            AirQualityReading.timestamp >= cutoff,
        )
        .order_by(AirQualityReading.timestamp.asc())
    )
    timestamps = list(rows)

    if not timestamps:
        return [
            {
                "gap_start": cutoff,
                "gap_end": now,
                "duration_minutes": int((now - cutoff).total_seconds() / 60),
            }
        ]

    gaps = []

    for i in range(len(timestamps) - 1):
        delta = timestamps[i + 1] - timestamps[i]
        minutes = int(delta.total_seconds() / 60)
        if minutes > threshold_minutes:
            gaps.append(
                {
                    "gap_start": timestamps[i],
                    "gap_end": timestamps[i + 1],
                    "duration_minutes": minutes,
                }
            )

    # Trailing gap: last reading to now
    trailing_minutes = int((now - timestamps[-1]).total_seconds() / 60)
    if trailing_minutes > threshold_minutes:
        gaps.append(
            {
                "gap_start": timestamps[-1],
                "gap_end": now,
                "duration_minutes": trailing_minutes,
            }
        )

    return gaps


async def get_city_comparison(session: AsyncSession) -> list[dict]:
    latest_subq = (
        select(
            AirQualityReading.location_id,
            func.max(AirQualityReading.timestamp).label("max_ts"),
        )
        .group_by(AirQualityReading.location_id)
        .subquery()
    )
    result = await session.execute(
        select(Location, AirQualityReading)
        .join(AirQualityReading, AirQualityReading.location_id == Location.location_id)
        .join(
            latest_subq,
            (latest_subq.c.location_id == AirQualityReading.location_id)
            & (latest_subq.c.max_ts == AirQualityReading.timestamp),
        )
        .order_by(AirQualityReading.aqi.desc())
    )
    return [
        {
            "city": loc.city,
            "country": loc.country,
            "latitude": float(loc.latitude),
            "longitude": float(loc.longitude),
            "latest_aqi": reading.aqi,
            "category": get_aqi_category(reading.aqi),
            "timestamp": reading.timestamp,
        }
        for loc, reading in result.all()
    ]
