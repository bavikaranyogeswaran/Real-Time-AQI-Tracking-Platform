import asyncio
import uuid

from sqlalchemy import func, select

from app.database import AsyncSessionLocal
from app.models.location import Location

CITIES = [
    {"city": "Colombo", "country": "Sri Lanka", "latitude": 6.9271, "longitude": 79.8612},
    {"city": "London", "country": "United Kingdom", "latitude": 51.5074, "longitude": -0.1278},
    {"city": "Delhi", "country": "India", "latitude": 28.6139, "longitude": 77.2090},
    {"city": "New York", "country": "United States", "latitude": 40.7128, "longitude": -74.0060},
    {"city": "Bangkok", "country": "Thailand", "latitude": 13.7563, "longitude": 100.5018},
    {"city": "Tokyo", "country": "Japan", "latitude": 35.6762, "longitude": 139.6503},
    {"city": "Paris", "country": "France", "latitude": 48.8566, "longitude": 2.3522},
    {"city": "Sydney", "country": "Australia", "latitude": -33.8688, "longitude": 151.2093},
    {"city": "Beijing", "country": "China", "latitude": 39.9042, "longitude": 116.4074},
    {"city": "Cairo", "country": "Egypt", "latitude": 30.0444, "longitude": 31.2357},
    {"city": "Mumbai", "country": "India", "latitude": 19.0760, "longitude": 72.8777},
    {"city": "Sao Paulo", "country": "Brazil", "latitude": -23.5505, "longitude": -46.6333},
]


async def seed():
    async with AsyncSessionLocal() as session:
        inserted = 0
        for data in CITIES:
            result = await session.execute(
                select(Location).where(func.lower(Location.city) == data["city"].lower())
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    Location(
                        location_id=str(uuid.uuid4()),
                        city=data["city"],
                        country=data["country"],
                        latitude=data["latitude"],
                        longitude=data["longitude"],
                        source="openweather",
                    )
                )
                inserted += 1
        await session.commit()
        print(f"Seeded {inserted} new cities. ({len(CITIES) - inserted} already existed)")


if __name__ == "__main__":
    asyncio.run(seed())
