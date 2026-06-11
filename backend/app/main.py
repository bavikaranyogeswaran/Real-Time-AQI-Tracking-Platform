import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api import alerts, analytics, aqi, locations
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.alert_rule import AlertRule
from pipeline.scheduler import scheduler, start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DEFAULT_RULES = [
    {"alert_type": "unhealthy", "threshold_value": 150},
    {"alert_type": "very_unhealthy", "threshold_value": 200},
    {"alert_type": "hazardous", "threshold_value": 300},
]


async def _seed_default_alert_rules() -> None:
    async with AsyncSessionLocal() as session:
        for rule_def in _DEFAULT_RULES:
            exists = await session.scalar(
                select(AlertRule).where(
                    AlertRule.alert_type == rule_def["alert_type"],
                    AlertRule.threshold_value == rule_def["threshold_value"],
                    AlertRule.location_id.is_(None),
                )
            )
            if not exists:
                session.add(
                    AlertRule(
                        rule_id=str(uuid.uuid4()),
                        location_id=None,
                        alert_type=rule_def["alert_type"],
                        threshold_value=rule_def["threshold_value"],
                        is_active=True,
                    )
                )
                logger.info(
                    "Seeded default alert rule: %s > %d",
                    rule_def["alert_type"],
                    rule_def["threshold_value"],
                )
        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _seed_default_alert_rules()
    start_scheduler()
    logger.info("Application started.")
    yield
    scheduler.shutdown(wait=False)
    logger.info("Application shutdown — scheduler stopped.")


app = FastAPI(
    title="Real-Time AQI Tracking Platform",
    description="Near-real-time air quality monitoring, forecasting, and alerting.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(locations.router, prefix="/api", tags=["Locations"])
app.include_router(aqi.router, prefix="/api", tags=["AQI"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "message": "AQI Platform is running"}
