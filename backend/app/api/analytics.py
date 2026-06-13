from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.location import Location
from app.rate_limit import limiter
from app.schemas.alert_performance_schema import AlertPerformanceOut
from app.schemas.analytics_schema import CityComparisonOut, ForecastAccuracyOut, GapOut, TrendOut
from app.services.analytics import (
    get_alert_performance,
    get_aqi_distribution,
    get_city_comparison,
    get_daily_averages,
    get_data_gaps,
    get_forecast_accuracy,
    get_hourly_averages,
)

router = APIRouter()

_PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


async def _get_location(session: AsyncSession, city: str) -> Location:
    result = await session.execute(select(Location).where(Location.city.ilike(city)))
    location = result.scalars().first()
    if not location:
        raise HTTPException(status_code=404, detail=f"City '{city}' not found")
    return location


@router.get("/analytics/city-comparison", response_model=list[CityComparisonOut])
@limiter.limit("30/minute")
async def city_comparison(request: Request, session: AsyncSession = Depends(get_db)):
    return await get_city_comparison(session)


@router.get("/analytics/trends", response_model=list[TrendOut])
@limiter.limit("30/minute")
async def trends(
    request: Request,
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
@limiter.limit("30/minute")
async def peak_hours(
    request: Request,
    city: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    return await get_hourly_averages(session, location.location_id)


@router.get("/analytics/distribution")
@limiter.limit("30/minute")
async def aqi_distribution(
    request: Request,
    city: str = Query(...),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    return await get_aqi_distribution(session, location.location_id)


@router.get("/analytics/forecast-accuracy", response_model=ForecastAccuracyOut)
@limiter.limit("30/minute")
async def forecast_accuracy_report(
    request: Request,
    city: str = Query(...),
    days: int = Query(default=7, ge=1, le=30),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    return await get_forecast_accuracy(session, location.location_id, days)


@router.get("/analytics/alert-performance", response_model=AlertPerformanceOut)
@limiter.limit("20/minute")
async def alert_performance(
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db),
):
    return await get_alert_performance(session, days)


@router.get("/analytics/gaps", response_model=list[GapOut])
@limiter.limit("30/minute")
async def data_gaps(
    request: Request,
    city: str = Query(...),
    lookback_hours: int = Query(default=24, ge=1, le=168),
    threshold_minutes: int = Query(default=20, ge=5, le=120),
    session: AsyncSession = Depends(get_db),
):
    location = await _get_location(session, city)
    return await get_data_gaps(session, location.location_id, lookback_hours, threshold_minutes)
