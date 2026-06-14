import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from app.models.air_quality import AirQualityReading
from app.models.alert import Alert
from app.models.location import Location
from app.services import bigquery_client as bq
from app.services.ingestion import get_aqi_category

logger = logging.getLogger(__name__)


async def get_daily_averages(location_id: str, days: int) -> list[dict]:
    return await _daily_averages_bq(location_id, days)


async def get_hourly_averages(location_id: str) -> list[dict]:
    return await _hourly_averages_bq(location_id)


async def get_aqi_distribution(location_id: str) -> list[dict]:
    return await _aqi_distribution_bq(location_id)


async def get_city_comparison() -> list[dict]:
    return await _city_comparison_bq()


async def get_forecast_accuracy(location_id: str, days: int) -> dict:
    return await _forecast_accuracy_bq(location_id, days)


async def get_city_ranking(days: int) -> list[dict]:
    return await _city_ranking_bq(days)


async def get_pollutant_trends(location_id: str, days: int) -> list[dict]:
    return await _pollutant_trends_bq(location_id, days)


async def get_dominant_pollutant(location_id: str, days: int) -> list[dict]:
    return await _dominant_pollutant_bq(location_id, days)


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


async def get_alert_performance(session: AsyncSession, days: int) -> dict:
    """Return alert counts by type, city, and day over the last `days` days."""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    total = await session.scalar(
        select(func.count()).where(Alert.created_at >= cutoff)
    ) or 0

    active = await session.scalar(
        select(func.count()).where(Alert.created_at >= cutoff, Alert.status == "active")
    ) or 0

    resolved = await session.scalar(
        select(func.count()).where(Alert.created_at >= cutoff, Alert.status == "resolved")
    ) or 0

    by_type_rows = (
        await session.execute(
            select(
                Alert.alert_type,
                func.count().label("count"),
                func.avg(Alert.actual_aqi).label("avg_aqi"),
            )
            .where(Alert.created_at >= cutoff)
            .group_by(Alert.alert_type)
            .order_by(func.count().desc())
        )
    ).all()
    by_type = [
        {"alert_type": r.alert_type, "count": r.count, "avg_aqi": round(float(r.avg_aqi), 1)}
        for r in by_type_rows
    ]

    by_city_rows = (
        await session.execute(
            select(Location.city, func.count().label("count"))
            .join(Alert, Alert.location_id == Location.location_id)
            .where(Alert.created_at >= cutoff)
            .group_by(Location.city)
            .order_by(func.count().desc())
            .limit(10)
        )
    ).all()
    by_city = [{"city": r.city, "count": r.count} for r in by_city_rows]

    date_col = cast(Alert.created_at, Date).label("date")
    daily_rows = (
        await session.execute(
            select(date_col, func.count().label("count"))
            .where(Alert.created_at >= cutoff)
            .group_by(date_col)
            .order_by(date_col.asc())
        )
    ).all()
    daily_counts = [{"date": r.date, "count": r.count} for r in daily_rows]

    return {
        "total": total,
        "active": active,
        "resolved": resolved,
        "by_type": by_type,
        "by_city": by_city,
        "daily_counts": daily_counts,
    }


async def _forecast_accuracy_bq(location_id: str, days: int) -> dict:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    now = datetime.now(UTC)
    readings_table = bq._table_id()
    predictions_table = bq._predictions_table_id()
    sql = f"""
        WITH predictions AS (
            SELECT prediction_id, forecast_for, predicted_aqi
            FROM `{predictions_table}`
            WHERE location_id = @location_id
              AND forecast_for >= @cutoff
              AND forecast_for <= @now
        ),
        actuals AS (
            SELECT timestamp, aqi
            FROM `{readings_table}`
            WHERE location_id = @location_id
              AND timestamp >= TIMESTAMP_SUB(@cutoff, INTERVAL 30 MINUTE)
              AND timestamp <= TIMESTAMP_ADD(@now, INTERVAL 30 MINUTE)
        ),
        matched AS (
            SELECT
                p.forecast_for,
                p.predicted_aqi,
                a.aqi AS actual_aqi,
                ROUND(p.predicted_aqi - a.aqi, 2) AS error,
                ROW_NUMBER() OVER (
                    PARTITION BY p.prediction_id
                    ORDER BY ABS(TIMESTAMP_DIFF(a.timestamp, p.forecast_for, MINUTE))
                ) AS rn
            FROM predictions p
            JOIN actuals a
              ON ABS(TIMESTAMP_DIFF(a.timestamp, p.forecast_for, MINUTE)) <= 30
        )
        SELECT forecast_for, predicted_aqi, actual_aqi, error
        FROM matched
        WHERE rn = 1
        ORDER BY forecast_for ASC
    """
    rows = await bq.run_query(sql, [
        bq.str_param("location_id", location_id),
        bq.ts_param("cutoff", cutoff),
        bq.ts_param("now", now),
    ])

    if not rows:
        return {"rows": [], "mae": 0.0, "rmse": 0.0, "sample_count": 0}

    result_rows = [
        {
            "forecast_for": row["forecast_for"],
            "predicted_aqi": float(row["predicted_aqi"]),
            "actual_aqi": int(row["actual_aqi"]),
            "error": float(row["error"]),
        }
        for row in rows
    ]
    errors = [r["error"] for r in result_rows]
    return {
        "rows": result_rows,
        "mae": round(sum(abs(e) for e in errors) / len(errors), 2),
        "rmse": round((sum(e ** 2 for e in errors) / len(errors)) ** 0.5, 2),
        "sample_count": len(result_rows),
    }


async def _city_ranking_bq(days: int) -> list[dict]:
    now = datetime.now(UTC)
    start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)
    table = bq._table_id()
    sql = f"""
        WITH current_period AS (
            SELECT city, country,
                   ROUND(AVG(aqi), 1)                                          AS avg_aqi,
                   MAX(aqi)                                                     AS max_aqi,
                   COUNT(DISTINCT IF(aqi > 150, DATE(timestamp), NULL))        AS unhealthy_days
            FROM `{table}`
            WHERE timestamp >= @start AND timestamp < @end
            GROUP BY city, country
        ),
        prev_period AS (
            SELECT city, ROUND(AVG(aqi), 1) AS prev_avg_aqi
            FROM `{table}`
            WHERE timestamp >= @prev_start AND timestamp < @start
            GROUP BY city
        )
        SELECT
            c.city, c.country, c.avg_aqi, c.max_aqi, c.unhealthy_days,
            p.prev_avg_aqi,
            CASE
                WHEN p.prev_avg_aqi IS NULL         THEN 'stable'
                WHEN p.prev_avg_aqi - c.avg_aqi > 5 THEN 'improving'
                WHEN c.avg_aqi - p.prev_avg_aqi > 5 THEN 'worsening'
                ELSE 'stable'
            END AS trend
        FROM current_period c
        LEFT JOIN prev_period p ON c.city = p.city
        ORDER BY c.avg_aqi DESC
    """
    rows = await bq.run_query(sql, [
        bq.ts_param("start", start),
        bq.ts_param("end", now),
        bq.ts_param("prev_start", prev_start),
    ])
    return [
        {
            "city": row["city"],
            "country": row["country"],
            "avg_aqi": float(row["avg_aqi"]),
            "max_aqi": int(row["max_aqi"]),
            "unhealthy_days": int(row["unhealthy_days"]),
            "prev_avg_aqi": float(row["prev_avg_aqi"]) if row["prev_avg_aqi"] is not None else None,
            "trend": row["trend"],
        }
        for row in rows
    ]


async def _pollutant_trends_bq(location_id: str, days: int) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    table = bq._table_id()
    sql = f"""
        SELECT
            DATE(timestamp) AS date,
            ROUND(AVG(pm25), 2) AS avg_pm25,
            ROUND(AVG(pm10), 2) AS avg_pm10,
            ROUND(AVG(co),   2) AS avg_co,
            ROUND(AVG(no2),  2) AS avg_no2,
            ROUND(AVG(so2),  2) AS avg_so2,
            ROUND(AVG(o3),   2) AS avg_o3
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
            "avg_pm25": float(row["avg_pm25"]) if row["avg_pm25"] is not None else None,
            "avg_pm10": float(row["avg_pm10"]) if row["avg_pm10"] is not None else None,
            "avg_co":   float(row["avg_co"])   if row["avg_co"]   is not None else None,
            "avg_no2":  float(row["avg_no2"])  if row["avg_no2"]  is not None else None,
            "avg_so2":  float(row["avg_so2"])  if row["avg_so2"]  is not None else None,
            "avg_o3":   float(row["avg_o3"])   if row["avg_o3"]   is not None else None,
        }
        for row in rows
    ]


async def _dominant_pollutant_bq(location_id: str, days: int) -> list[dict]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    table = bq._table_id()
    sql = f"""
        SELECT pollutant, label, avg_value, safe_limit, exceedance_count FROM (
            SELECT 'pm25' AS pollutant, 'PM2.5' AS label,
                   ROUND(AVG(pm25), 2) AS avg_value, 15.0 AS safe_limit,
                   COUNTIF(pm25 > 15) AS exceedance_count
            FROM `{table}` WHERE location_id = @location_id AND timestamp >= @cutoff AND pm25 IS NOT NULL
            UNION ALL
            SELECT 'pm10', 'PM10', ROUND(AVG(pm10), 2), 45.0, COUNTIF(pm10 > 45)
            FROM `{table}` WHERE location_id = @location_id AND timestamp >= @cutoff AND pm10 IS NOT NULL
            UNION ALL
            SELECT 'co', 'CO', ROUND(AVG(co), 2), 4000.0, COUNTIF(co > 4000)
            FROM `{table}` WHERE location_id = @location_id AND timestamp >= @cutoff AND co IS NOT NULL
            UNION ALL
            SELECT 'no2', 'NO₂', ROUND(AVG(no2), 2), 25.0, COUNTIF(no2 > 25)
            FROM `{table}` WHERE location_id = @location_id AND timestamp >= @cutoff AND no2 IS NOT NULL
            UNION ALL
            SELECT 'so2', 'SO₂', ROUND(AVG(so2), 2), 40.0, COUNTIF(so2 > 40)
            FROM `{table}` WHERE location_id = @location_id AND timestamp >= @cutoff AND so2 IS NOT NULL
            UNION ALL
            SELECT 'o3', 'O₃', ROUND(AVG(o3), 2), 100.0, COUNTIF(o3 > 100)
            FROM `{table}` WHERE location_id = @location_id AND timestamp >= @cutoff AND o3 IS NOT NULL
        )
        WHERE avg_value IS NOT NULL
        ORDER BY exceedance_count DESC
    """
    rows = await bq.run_query(
        sql,
        [bq.str_param("location_id", location_id), bq.ts_param("cutoff", cutoff)],
    )
    return [
        {
            "pollutant": row["pollutant"],
            "label": row["label"],
            "avg_value": float(row["avg_value"]),
            "safe_limit": float(row["safe_limit"]),
            "exceedance_count": int(row["exceedance_count"]),
        }
        for row in rows
    ]


async def _city_comparison_bq() -> list[dict]:
    table = bq._table_id()
    sql = f"""
        SELECT city, country, latitude, longitude, aqi, timestamp
        FROM (
            SELECT
                city, country, latitude, longitude, aqi, timestamp,
                ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY timestamp DESC) AS rn
            FROM `{table}`
            WHERE latitude IS NOT NULL AND longitude IS NOT NULL
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
