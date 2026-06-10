import httpx
from app.config import settings

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


async def fetch_air_quality(lat: float, lon: float) -> dict:
    """Call OpenWeather Air Pollution API and return the raw response dict."""
    params = {"lat": lat, "lon": lon, "appid": settings.openweather_api_key}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPENWEATHER_URL, params=params)
        response.raise_for_status()
        return response.json()
