import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.location import Location
from app.services.ingestion import ingest_location

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def ingest_all_locations() -> None:
    """Fetch and store fresh AQI readings for every location in the database."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Location))
        locations = result.scalars().all()

    for location in locations:
        try:
            async with AsyncSessionLocal() as session:
                await ingest_location(session, location)
        except Exception as exc:
            logger.error("Unexpected error ingesting %s: %s", location.city, exc)


async def run_hourly_forecast() -> None:
    """Run AQI forecast model for all locations. Wired in Phase 5."""
    logger.info("Hourly forecast job triggered — ML service not yet wired.")


async def retrain_models_daily() -> None:
    """Retrain ML models with the latest data. Wired in Phase 5."""
    logger.info("Daily model retraining triggered — ML service not yet wired.")


def start_scheduler() -> None:
    scheduler.add_job(
        ingest_all_locations,
        trigger="interval",
        minutes=10,
        id="ingest_all_locations",
        replace_existing=True,
    )
    scheduler.add_job(
        run_hourly_forecast,
        trigger="interval",
        hours=1,
        id="run_hourly_forecast",
        replace_existing=True,
    )
    scheduler.add_job(
        retrain_models_daily,
        trigger="cron",
        hour=2,
        minute=0,
        id="retrain_models_daily",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — ingestion every 10 min, forecast every hour, retrain daily at 02:00.")
