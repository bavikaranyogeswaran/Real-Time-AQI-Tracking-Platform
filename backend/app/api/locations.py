from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.location import Location
from app.schemas.location_schema import LocationOut

router = APIRouter()


@router.get("/locations", response_model=list[LocationOut])
async def get_locations(session: AsyncSession = Depends(get_db)):
    result = await session.execute(select(Location).order_by(Location.city))
    return result.scalars().all()
