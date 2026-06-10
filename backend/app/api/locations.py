import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.location import Location
from app.schemas.location_schema import LocationIn, LocationOut

router = APIRouter()


@router.get("/locations", response_model=list[LocationOut])
async def get_locations(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Location).order_by(Location.city))
    return result.scalars().all()


@router.post("/locations", response_model=LocationOut, status_code=201)
async def create_location(body: LocationIn, session: AsyncSession = Depends(get_db)):
    existing = await session.scalar(
        select(Location).where(func.lower(Location.city) == body.city.lower())
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Location '{body.city}' already exists.")
    location = Location(
        location_id=str(uuid.uuid4()),
        city=body.city,
        country=body.country,
        latitude=body.latitude,
        longitude=body.longitude,
    )
    session.add(location)
    await session.commit()
    await session.refresh(location)
    return location
