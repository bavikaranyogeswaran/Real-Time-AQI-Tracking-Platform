import httpx
from app.config import settings

OPENWEATHER_URL = "http://api.openweathermap.org/data/2.5/air_pollution"


async def fetch_air_quality(lat: float, lon: float) -> dict:
    """Call OpenWeather Air Pollution API and return the raw response dict."""
    params = {"lat": lat, "lon": lon, "appid": settings.openweather_api_key}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(OPENWEATHER_URL, params=params)
        response.raise_for_status()
        return response.json()
