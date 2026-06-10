import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.air_quality import AirQualityReading
from app.models.location import Location

logger = logging.getLogger(__name__)

OPENWEATHER_URL = "http://api.openweathermap.org/data/2.5/air_pollution"

# US EPA PM2.5 breakpoints: (C_lo, C_hi, AQI_lo, AQI_hi)
_PM25_BREAKPOINTS = [
    (0.0,   12.0,  0,   50),
    (12.1,  35.4,  51,  100),
    (35.5,  55.4,  101, 150),
    (55.5,  150.4, 151, 200),
    (150.5, 250.4, 201, 300),
    (250.5, 350.4, 301, 400),
    (350.5, 500.4, 401, 500),
]


def calculate_aqi_from_pm25(pm25_ugm3: float) -> int:
    """Convert PM2.5 concentration (μg/m³) to US EPA AQI using linear interpolation."""
    pm25 = round(pm25_ugm3, 1)
    for c_lo, c_hi, aqi_lo, aqi_hi in _PM25_BREAKPOINTS:
        if c_lo <= pm25 <= c_hi:
            aqi = (aqi_hi - aqi_lo) / (c_hi - c_lo) * (pm25 - c_lo) + aqi_lo
            return round(aqi)
    return 500 if pm25 > 500.4 else 0


def get_aqi_category(aqi: int) -> str:
    """Map an AQI value to its US EPA health category label."""
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Moderate"
    if aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    if aqi <= 200:
        return "Unhealthy"
    if aqi <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def validate_reading(data: dict) -> bool:
    """Return True if the API response has the required fields and valid values."""
    try:
        entry = data["list"][0]
        components = entry["components"]
        pm25 = components.get("pm2_5")

        if pm25 is None:
            return False
        if pm25 < 0:
            return False
        if pm25 > 500.4:  # beyond top EPA breakpoint — treat as sensor error
            return False

        aqi = calculate_aqi_from_pm25(pm25)
        if not (0 <= aqi <= 999):
            return False

        pollutants = ["pm10", "co", "no2", "so2", "o3"]
        for key in pollutants:
            val = components.get(key)
            if val is not None and val < 0:
                return False

        return True
    except (KeyError, IndexError, TypeError):
        return False


async def save_reading(
    session: AsyncSession, location_id: str, data: dict
) -> AirQualityReading:
    """Parse a validated API response and persist a new AirQualityReading row.

    Returns the existing row unchanged if one already exists for this
    (location_id, timestamp) pair — prevents duplicate inserts when the
    scheduler fires more than once within the same API polling window.
    """
    entry = data["list"][0]
    components = entry["components"]
    pm25 = components.get("pm2_5", 0.0)
    aqi = calculate_aqi_from_pm25(pm25)
    timestamp = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)

    existing = await session.scalar(
        select(AirQualityReading).where(
            AirQualityReading.location_id == location_id,
            AirQualityReading.timestamp == timestamp,
        )
    )
    if existing:
        logger.debug("Duplicate reading for location %s at %s — skipping insert.", location_id, timestamp)
        return existing

    reading = AirQualityReading(
        reading_id=str(uuid.uuid4()),
        location_id=location_id,
        timestamp=timestamp,
        aqi=aqi,
        pm25=pm25,
        pm10=components.get("pm10"),
        co=components.get("co"),
        no2=components.get("no2"),
        so2=components.get("so2"),
        o3=components.get("o3"),
        data_source="openweather",
    )
    session.add(reading)
    await session.flush()
    return reading


async def is_outlier(session: AsyncSession, location_id: str, aqi: int) -> bool:
    """Return True if aqi is a statistical spike relative to recent history.

    Uses a 3-sigma z-score over the last 10 readings. Requires at least 3 prior
    readings; skips the check (returns False) when history is too thin.
    When all historical readings are identical (std=0), flags any deviation > 100
    AQI units as a spike.
    """
    rows = await session.scalars(
        select(AirQualityReading.aqi)
        .where(AirQualityReading.location_id == location_id)
        .order_by(AirQualityReading.timestamp.desc())
        .limit(10)
    )
    recent = list(rows)
    if len(recent) < 3:
        return False

    mean = sum(recent) / len(recent)
    std = (sum((x - mean) ** 2 for x in recent) / len(recent)) ** 0.5

    if std == 0:
        return abs(aqi - mean) > 100

    return abs(aqi - mean) / std > 3.0


async def ingest_location(session: AsyncSession, location: Location) -> AirQualityReading | None:
    """Fetch, validate, and save one reading for the given location. Returns the saved
    reading, or None if the API call failed or the response failed validation."""
    try:
        data = await fetch_air_quality(location.latitude, location.longitude)
    except httpx.HTTPError as exc:
        logger.warning("API fetch failed for %s: %s", location.city, exc)
        return None

    if not validate_reading(data):
        logger.warning("Invalid reading received for %s — skipping.", location.city)
        return None

    aqi = calculate_aqi_from_pm25(data["list"][0]["components"].get("pm2_5", 0.0))
    if await is_outlier(session, location.location_id, aqi):
        logger.warning("Outlier reading (AQI %d) for %s — skipping.", aqi, location.city)
        return None

    reading = await save_reading(session, location.location_id, data)
    await session.commit()
    logger.info("Ingested AQI %d for %s.", reading.aqi, location.city)
    return reading


async def fetch_air_quality(lat: float, lon: float) -> dict:
    """Call OpenWeather Air Pollution API and return the raw response dict."""
    params = {"lat": lat, "lon": lon, "appid": settings.openweather_api_key}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPENWEATHER_URL, params=params)
        response.raise_for_status()
        return response.json()
