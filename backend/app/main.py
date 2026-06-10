import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, analytics, aqi, locations
from pipeline.scheduler import start_scheduler, scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    allow_origins=["http://localhost:5173"],
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
