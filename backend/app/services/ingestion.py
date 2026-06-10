import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.air_quality import AirQualityReading

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
    """Parse a validated API response and persist a new AirQualityReading row."""
    entry = data["list"][0]
    components = entry["components"]
    pm25 = components.get("pm2_5", 0.0)
    aqi = calculate_aqi_from_pm25(pm25)
    timestamp = datetime.fromtimestamp(entry["dt"], tz=timezone.utc)

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


async def fetch_air_quality(lat: float, lon: float) -> dict:
    """Call OpenWeather Air Pollution API and return the raw response dict."""
    params = {"lat": lat, "lon": lon, "appid": settings.openweather_api_key}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPENWEATHER_URL, params=params)
        response.raise_for_status()
        return response.json()
