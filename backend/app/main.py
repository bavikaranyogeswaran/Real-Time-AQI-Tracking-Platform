import logging
import sys
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import _rate_limit_exceeded_handler
from sqlalchemy import select, text

from app.api import alerts, analytics, aqi, locations
from app.config import settings
from app.database import AsyncSessionLocal, init_db
from app.services import bigquery_client as bq
from app.logging_config import configure_logging
from app.metrics import http_requests_total
from app.models.alert_rule import AlertRule
from app.rate_limit import limiter
from app.security_headers import SecurityHeadersMiddleware
from pipeline.scheduler import scheduler, start_scheduler

configure_logging(settings.log_format)
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


def _validate_config() -> None:
    """Fail fast if required secrets are missing; warn about optional ones."""
    errors: list[str] = []

    if not settings.database_url:
        errors.append(
            "DATABASE_URL is not set. "
            "Add DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db to your .env file."
        )

    if errors:
        for msg in errors:
            logger.critical("CONFIG ERROR: %s", msg)
        raise RuntimeError(f"Missing required configuration: {'; '.join(errors)}")

    if not settings.openweather_api_key:
        logger.warning(
            "OPENWEATHER_API_KEY is not set — "
            "AQI ingestion will fail until OPENWEATHER_API_KEY is configured"
        )
    if not settings.smtp_username:
        logger.warning("SMTP credentials not configured — email alert notifications are disabled")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _validate_config()
    init_db()
    await _seed_default_alert_rules()
    if bq.is_enabled():
        try:
            await bq.ensure_dataset_and_table()
            logger.info("BigQuery warehouse ready: %s", bq._table_id())
        except Exception as exc:
            logger.error("BigQuery init failed — warehouse tier disabled for this run: %s", exc)
    else:
        logger.info("BigQuery not configured (BIGQUERY_PROJECT_ID unset) — using PostgreSQL only.")
    start_scheduler()
    db_host = urlparse(settings.database_url).hostname or "unknown"
    job_names = ",".join(j.id for j in scheduler.get_jobs())
    logger.info(
        "AQI Platform v%s started | python=%s | db_host=%s | jobs=[%s]",
        app.version,
        sys.version.split()[0],
        db_host,
        job_names,
    )
    yield
    scheduler.shutdown(wait=False)
    logger.info("Application shutdown — scheduler stopped.")


app = FastAPI(
    title="Real-Time AQI Tracking Platform",
    description="Near-real-time air quality monitoring, forecasting, and alerting.",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)

    http_requests_total.labels(
        method=request.method,
        path=request.url.path,
        status_code=str(response.status_code),
    ).inc()

    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(locations.router, prefix="/api", tags=["Locations"])
app.include_router(aqi.router, prefix="/api", tags=["AQI"])
app.include_router(alerts.router, prefix="/api", tags=["Alerts"])
app.include_router(analytics.router, prefix="/api", tags=["Analytics"])


@app.get("/metrics", include_in_schema=False)
async def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/live", tags=["Health"])
async def liveness():
    """Liveness probe — 200 as long as the process is alive."""
    return {"status": "alive"}


@app.get("/ready", tags=["Health"])
async def readiness():
    """Readiness probe — 503 until the database is reachable."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unreachable: {exc}") from exc
    return {"status": "ready"}


@app.get("/health", tags=["Health"])
async def health():
    """Deep health check — DB ping + scheduler job count."""
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    return {
        "status": "ok",
        "db": db_status,
        "scheduler_jobs": len(scheduler.get_jobs()),
    }
