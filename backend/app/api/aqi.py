from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.air_quality import AirQualityReading
from app.models.location import Location
from app.models.prediction import AQIPrediction
from app.rate_limit import limiter
from app.schemas.aqi_schema import CurrentAQIOut, ForecastOut, HistoryAQIOut, PollutantOut
from app.services.ingestion import get_aqi_category

router = APIRouter()


async def _get_location(session: AsyncSession, city: str) -> Location:
    result = await session.execute(select(Location).where(Location.city.ilike(city)))
    location = result.scalars().first()
    if not location:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
    return location


@router.get("/aqi/current", response_model=CurrentAQIOut)
@limiter.limit("60/minute")
async def get_current_aqi(
    request: Request,
    city: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    result = await session.execute(
        select(AirQualityReading)
        .where(AirQualityReading.location_id == location.location_id)
        .order_by(AirQualityReading.timestamp.desc())
        .limit(1)
    )
    reading = result.scalars().first()
    if not reading:
        raise HTTPException(status_code=404, detail=f"No readings found for '{city}'")

    return {
        "reading_id": reading.reading_id,
        "location_id": reading.location_id,
        "city": location.city,
        "timestamp": reading.timestamp,
        "aqi": reading.aqi,
        "category": get_aqi_category(reading.aqi),
        "pm25": reading.pm25,
        "pm10": reading.pm10,
        "co": reading.co,
        "no2": reading.no2,
        "so2": reading.so2,
        "o3": reading.o3,
        "data_source": reading.data_source,
    }


@router.get("/aqi/history", response_model=list[HistoryAQIOut])
@limiter.limit("30/minute")
async def get_history(
    request: Request,
    city: str = Query(...),
    days: int = Query(default=7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    cutoff = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(
        select(AirQualityReading)
        .where(
            AirQualityReading.location_id == location.location_id,
            AirQualityReading.timestamp >= cutoff,
        )
        .order_by(AirQualityReading.timestamp.desc())
    )
    readings = result.scalars().all()
    return [
        {
            "reading_id": r.reading_id,
            "timestamp": r.timestamp,
            "aqi": r.aqi,
            "category": get_aqi_category(r.aqi),
            "pm25": r.pm25,
            "pm10": r.pm10,
            "co": r.co,
            "no2": r.no2,
            "so2": r.so2,
            "o3": r.o3,
        }
        for r in readings
    ]


@router.get("/aqi/pollutants", response_model=PollutantOut)
@limiter.limit("30/minute")
async def get_pollutants(
    request: Request,
    city: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    result = await session.execute(
        select(AirQualityReading)
        .where(AirQualityReading.location_id == location.location_id)
        .order_by(AirQualityReading.timestamp.desc())
        .limit(1)
    )
    reading = result.scalars().first()
    if not reading:
        raise HTTPException(status_code=404, detail=f"No readings found for '{city}'")
    return reading


@router.get("/aqi/forecast", response_model=list[ForecastOut])
@limiter.limit("30/minute")
async def get_forecast(
    request: Request,
    city: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    result = await session.execute(
        select(AQIPrediction)
        .where(AQIPrediction.location_id == location.location_id)
        .order_by(AQIPrediction.forecast_for.asc())
        .limit(24)
    )
    return result.scalars().all()
