from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.location import Location
from app.schemas.analytics_schema import CityComparisonOut, GapOut, TrendOut
from app.services.analytics import (
    get_aqi_distribution,
    get_city_comparison,
    get_daily_averages,
    get_data_gaps,
    get_hourly_averages,
)

router = APIRouter()

_PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


async def _get_location(session: AsyncSession, city: str) -> Location:
    result = await session.execute(
        select(Location).where(Location.city.ilike(city))
    )
    location = result.scalars().first()
    if not location:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
    return location


@router.get("/analytics/city-comparison", response_model=list[CityComparisonOut])
async def city_comparison(session: AsyncSession = Depends(get_db)):
    return await get_city_comparison(session)


@router.get("/analytics/trends", response_model=list[TrendOut])
async def trends(
    city: str = Query(...),
    period: str = Query(default="weekly"),
    session: AsyncSession = Depends(get_db),
):
    if period not in _PERIOD_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid period '{period}'. Choose from: {', '.join(_PERIOD_DAYS)}",
        )
    location = await _get_location(session, city)
    return await get_daily_averages(session, location.location_id, _PERIOD_DAYS[period])


@router.get("/analytics/peak-hours")
async def peak_hours(
    city: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    return await get_hourly_averages(session, location.location_id)


@router.get("/analytics/distribution")
async def aqi_distribution(
    city: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    return await get_aqi_distribution(session, location.location_id)


@router.get("/analytics/gaps", response_model=list[GapOut])
async def data_gaps(
    city: str = Query(...),
    lookback_hours: int = Query(default=24, ge=1, le=168),
    threshold_minutes: int = Query(default=20, ge=5, le=120),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    return await get_data_gaps(
        session, location.location_id, lookback_hours, threshold_minutes
    )
