import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.models.air_quality import AirQualityReading
from app.models.location import Location
from app.services import bigquery_client as bq
from app.services.ingestion import get_aqi_category

logger = logging.getLogger(__name__)


async def get_daily_averages(session: AsyncSession, location_id: str, days: int) -> list[dict]:
    if bq.is_enabled():
        try:
            return await _daily_averages_bq(location_id, days)
        except Exception as exc:
            logger.warning("BigQuery daily-averages failed, falling back to PostgreSQL: %s", exc)
    return await _daily_averages_pg(session, location_id, days)


async def get_hourly_averages(session: AsyncSession, location_id: str) -> list[dict]:
    if bq.is_enabled():
        try:
            return await _hourly_averages_bq(location_id)
        except Exception as exc:
            logger.warning("BigQuery hourly-averages failed, falling back to PostgreSQL: %s", exc)
    return await _hourly_averages_pg(session, location_id)


async def get_aqi_distribution(session: AsyncSession, location_id: str) -> list[dict]:
    if bq.is_enabled():
        try:
            return await _aqi_distribution_bq(location_id)
        except Exception as exc:
            logger.warning("BigQuery distribution failed, falling back to PostgreSQL: %s", exc)
    return await _aqi_distribution_pg(session, location_id)


async def get_city_comparison(session: AsyncSession) -> list[dict]:
    if bq.is_enabled():
        try:
            return await _city_comparison_bq()
        except Exception as exc:
            logger.warning("BigQuery city-comparison failed, falling back to PostgreSQL: %s", exc)
    return await _city_comparison_pg(session)


async def get_data_gaps(
    session: AsyncSession,
    location_id: str,
    lookback_hours: int = 24,
    threshold_minutes: int = 20,
) -> list[dict]:
    """Gap detection queries recent timestamps — kept on PostgreSQL for low latency."""
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


# ── PostgreSQL implementations ────────────────────────────────────────────────


async def _daily_averages_pg(session: AsyncSession, location_id: str, days: int) -> list[dict]:
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


async def _hourly_averages_pg(session: AsyncSession, location_id: str) -> list[dict]:
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


async def _aqi_distribution_pg(session: AsyncSession, location_id: str) -> list[dict]:
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


async def _city_comparison_pg(session: AsyncSession) -> list[dict]:
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


# ── BigQuery implementations ──────────────────────────────────────────────────


async def _daily_averages_bq(location_id: str, days: int) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    table = bq._table_id()
    sql = f"""
        SELECT
            DATE(timestamp) AS date,
            ROUND(AVG(aqi), 1) AS avg_aqi,
            MIN(aqi) AS min_aqi,
            MAX(aqi) AS max_aqi
        FROM `{table}`
        WHERE location_id = @location_id
          AND timestamp >= @cutoff
        GROUP BY date
        ORDER BY date ASC
    """
    rows = await bq.run_query(
        sql,
        [bq.str_param("location_id", location_id), bq.ts_param("cutoff", cutoff)],
    )
    return [
        {
            "date": row["date"],
            "avg_aqi": float(row["avg_aqi"]),
            "min_aqi": int(row["min_aqi"]),
            "max_aqi": int(row["max_aqi"]),
        }
        for row in rows
    ]


async def _hourly_averages_bq(location_id: str) -> list[dict]:
    table = bq._table_id()
    sql = f"""
        SELECT
            EXTRACT(HOUR FROM timestamp) AS hour,
            ROUND(AVG(aqi), 1) AS avg_aqi
        FROM `{table}`
        WHERE location_id = @location_id
        GROUP BY hour
        ORDER BY hour ASC
    """
    rows = await bq.run_query(sql, [bq.str_param("location_id", location_id)])
    return [{"hour": int(row["hour"]), "avg_aqi": float(row["avg_aqi"])} for row in rows]


async def _aqi_distribution_bq(location_id: str) -> list[dict]:
    table = bq._table_id()
    sql = f"""
        SELECT
            CASE
                WHEN aqi <= 50  THEN 'Good'
                WHEN aqi <= 100 THEN 'Moderate'
                WHEN aqi <= 150 THEN 'Unhealthy for Sensitive Groups'
                WHEN aqi <= 200 THEN 'Unhealthy'
                WHEN aqi <= 300 THEN 'Very Unhealthy'
                ELSE 'Hazardous'
            END AS category,
            COUNT(*) AS count
        FROM `{table}`
        WHERE location_id = @location_id
        GROUP BY category
        ORDER BY count DESC
    """
    rows = await bq.run_query(sql, [bq.str_param("location_id", location_id)])
    return [{"category": row["category"], "count": int(row["count"])} for row in rows]


async def _city_comparison_bq() -> list[dict]:
    table = bq._table_id()
    sql = f"""
        SELECT city, country, latitude, longitude, aqi, timestamp
        FROM (
            SELECT
                city, country, latitude, longitude, aqi, timestamp,
                ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY timestamp DESC) AS rn
            FROM `{table}`
        )
        WHERE rn = 1
        ORDER BY aqi DESC
    """
    rows = await bq.run_query(sql)
    return [
        {
            "city": row["city"],
            "country": row["country"],
            "latitude": float(row["latitude"]) if row["latitude"] is not None else None,
            "longitude": float(row["longitude"]) if row["longitude"] is not None else None,
            "latest_aqi": int(row["aqi"]),
            "category": get_aqi_category(int(row["aqi"])),
            "timestamp": row["timestamp"],
        }
        for row in rows
    ]
