import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.alert_rule import AlertRule

logger = logging.getLogger(__name__)

_DEDUP_WINDOW = timedelta(minutes=60)


async def check_threshold_rules(
    session: AsyncSession, location_id: str, aqi: int
) -> list[AlertRule]:
    """Return active rules whose threshold is breached by the given AQI.

    Matches rules scoped to this location AND global rules (location_id IS NULL).
    """
    result = await session.execute(
        select(AlertRule).where(
            AlertRule.is_active.is_(True),
            AlertRule.threshold_value < aqi,
            or_(
                AlertRule.location_id == location_id,
                AlertRule.location_id.is_(None),
            ),
        )
    )
    return result.scalars().all()


async def create_alert(
    session: AsyncSession,
    location_id: str,
    alert_type: str,
    threshold_value: int,
    actual_aqi: int,
) -> Alert | None:
    """Insert an Alert row, skipping if an identical alert exists within the last 60 min."""
    dedup_cutoff = datetime.now(timezone.utc) - _DEDUP_WINDOW
    existing = await session.execute(
        select(Alert).where(
            and_(
                Alert.location_id == location_id,
                Alert.alert_type == alert_type,
                Alert.threshold_value == threshold_value,
                Alert.status == "active",
                Alert.created_at >= dedup_cutoff,
            )
        )
    )
    if existing.scalars().first():
        logger.debug(
            "Dedup: skipping duplicate %s alert for location %s.", alert_type, location_id
        )
        return None

    alert = Alert(
        alert_id=str(uuid.uuid4()),
        location_id=location_id,
        alert_type=alert_type,
        threshold_value=threshold_value,
        actual_aqi=actual_aqi,
        status="active",
        created_at=datetime.now(timezone.utc),
    )
    session.add(alert)
    await session.flush()
    logger.info(
        "Alert created — type=%s, location=%s, AQI=%d (threshold %d).",
        alert_type, location_id, actual_aqi, threshold_value,
    )
    return alert


async def resolve_alert(session: AsyncSession, alert_id: str) -> Alert | None:
    """Set alert status to 'resolved'. Returns the updated Alert, or None if not found."""
    result = await session.execute(select(Alert).where(Alert.alert_id == alert_id))
    alert = result.scalars().first()
    if not alert:
        return None
    alert.status = "resolved"
    await session.flush()
    return alert
