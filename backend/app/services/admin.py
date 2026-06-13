import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.air_quality import AirQualityReading
from app.models.alert import Alert
from app.models.location import Location

logger = logging.getLogger(__name__)


async def get_admin_summary(session: AsyncSession) -> dict:
    """Return system-wide aggregate stats for the admin dashboard."""
    now = datetime.now(UTC)
    cutoff_7d = now - timedelta(days=7)

    # ── Scalar aggregates ─────────────────────────────────────────────────────
    total_readings = await session.scalar(
        select(func.count()).select_from(AirQualityReading)
    ) or 0

    source_rows = (
        await session.execute(
            select(AirQualityReading.data_source, func.count().label("n"))
            .group_by(AirQualityReading.data_source)
        )
    ).all()
    readings_by_source: dict[str, int] = {row.data_source or "unknown": row.n for row in source_rows}

    alerts_active = await session.scalar(
        select(func.count()).where(Alert.status == "active")
    ) or 0

    alerts_total_7d = await session.scalar(
        select(func.count()).where(Alert.created_at >= cutoff_7d)
    ) or 0

    cities_monitored = await session.scalar(
        select(func.count()).select_from(Location)
    ) or 0

    # ── Per-city status (triple join with two subqueries) ─────────────────────
    latest_subq = (
        select(
            AirQualityReading.location_id,
            func.max(AirQualityReading.timestamp).label("max_ts"),
        )
        .group_by(AirQualityReading.location_id)
        .subquery()
    )

    week_subq = (
        select(
            AirQualityReading.location_id,
            func.count().label("count_7d"),
        )
        .where(AirQualityReading.timestamp >= cutoff_7d)
        .group_by(AirQualityReading.location_id)
        .subquery()
    )

    city_rows = (
        await session.execute(
            select(
                Location.city,
                Location.country,
                AirQualityReading.aqi,
                AirQualityReading.timestamp,
                AirQualityReading.data_source,
                func.coalesce(week_subq.c.count_7d, 0).label("reading_count_7d"),
            )
            .outerjoin(latest_subq, latest_subq.c.location_id == Location.location_id)
            .outerjoin(
                AirQualityReading,
                (AirQualityReading.location_id == Location.location_id)
                & (AirQualityReading.timestamp == latest_subq.c.max_ts),
            )
            .outerjoin(week_subq, week_subq.c.location_id == Location.location_id)
            .order_by(AirQualityReading.aqi.desc().nulls_last())
        )
    ).all()

    city_status = [
        {
            "city": row.city,
            "country": row.country,
            "latest_aqi": row.aqi,
            "last_reading_at": row.timestamp,
            "reading_count_7d": row.reading_count_7d,
            "data_source": row.data_source,
        }
        for row in city_rows
    ]

    return {
        "total_readings": total_readings,
        "readings_by_source": readings_by_source,
        "alerts_active": alerts_active,
        "alerts_total_7d": alerts_total_7d,
        "cities_monitored": cities_monitored,
        "city_status": city_status,
    }
