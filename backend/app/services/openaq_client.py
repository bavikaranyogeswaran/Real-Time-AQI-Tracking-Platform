"""OpenAQ v3 client.

For each (lat, lon) finds the nearest station that has a recent PM2.5 reading,
then returns its measurements in the same normalized shape that
save_reading() expects:

    {"list": [{"dt": <unix int>, "components": {"pm2_5": float, ...}}]}

Readings older than MAX_AGE_HOURS are skipped so stale offline stations
don't pollute the training data.
"""

import logging
from datetime import UTC, datetime, timedelta

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAQ_BASE = "https://api.openaq.org/v3"
_SEARCH_RADIUS_M = 25_000  # 25 km
_MAX_AGE = timedelta(hours=2)

# OpenAQ parameter name → normalized component key used by save_reading()
_PARAM_TO_KEY: dict[str, str] = {
    "pm25": "pm2_5",
    "pm10": "pm10",
    "no2": "no2",
    "so2": "so2",
    "co": "co",
    "o3": "o3",
}


def _headers() -> dict[str, str]:
    h: dict[str, str] = {"Accept": "application/json"}
    if settings.openaq_api_key:
        h["X-API-Key"] = settings.openaq_api_key
    return h


async def fetch_latest(lat: float, lon: float) -> dict | None:
    """Return a normalized measurement dict for the nearest OpenAQ station, or None.

    Searches within 25 km ordered by distance. Picks the first result that has
    a non-stale PM2.5 value. Skips stations whose last update is older than
    MAX_AGE (2 h) so offline sensors don't inject outdated readings.
    """
    params: dict[str, str | int] = {
        "coordinates": f"{lat},{lon}",
        "radius": _SEARCH_RADIUS_M,
        "limit": 10,
        "order_by": "distance",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{OPENAQ_BASE}/locations",
                params=params,
                headers=_headers(),
            )
            resp.raise_for_status()
            results: list[dict] = resp.json().get("results", [])
    except Exception as exc:
        logger.warning("OpenAQ search failed (lat=%.4f, lon=%.4f): %s", lat, lon, exc)
        return None

    now = datetime.now(UTC)

    for station in results:
        components: dict[str, float | None] = {v: None for v in _PARAM_TO_KEY.values()}
        reading_ts: datetime | None = None
        has_pm25 = False

        for param in station.get("parameters", []):
            key = _PARAM_TO_KEY.get(param.get("name", ""))
            if key is None:
                continue
            last_value = param.get("lastValue")
            if last_value is None:
                continue
            components[key] = float(last_value)
            if key == "pm2_5":
                has_pm25 = True
                raw_ts = param.get("lastUpdated")
                if raw_ts:
                    try:
                        reading_ts = datetime.fromisoformat(
                            raw_ts.replace("Z", "+00:00")
                        )
                    except ValueError:
                        pass

        if not has_pm25:
            continue

        if reading_ts is not None and (now - reading_ts) > _MAX_AGE:
            logger.debug(
                "OpenAQ station %s: last reading %s is stale — skipping.",
                station.get("id"),
                reading_ts.isoformat(),
            )
            continue

        dt = int((reading_ts or now).timestamp())
        return {"list": [{"dt": dt, "components": components}]}

    logger.debug(
        "No fresh OpenAQ station with PM2.5 within %d m of (%.4f, %.4f).",
        _SEARCH_RADIUS_M,
        lat,
        lon,
    )
    return None
