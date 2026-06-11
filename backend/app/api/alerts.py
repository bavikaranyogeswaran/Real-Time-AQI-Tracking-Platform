import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.schemas.alert_schema import AlertOut, AlertRuleIn
from app.services.alert_engine import resolve_alert as engine_resolve_alert

router = APIRouter()


@router.get("/alerts", response_model=list[AlertOut])
async def get_alerts(session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Alert).where(Alert.status == "active").order_by(Alert.created_at.desc())
    )
    return result.scalars().all()


@router.post("/alerts/rules", status_code=201)
async def create_alert_rule(
    body: AlertRuleIn,
    session: AsyncSession = Depends(get_db),
):
    rule = AlertRule(
        rule_id=str(uuid.uuid4()),
        location_id=body.location_id,
        alert_type=body.alert_type,
        threshold_value=body.threshold_value,
        is_active=True,
    )
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return {
        "rule_id": rule.rule_id,
        "location_id": rule.location_id,
        "alert_type": rule.alert_type,
        "threshold_value": rule.threshold_value,
        "is_active": rule.is_active,
    }


@router.patch("/alerts/{alert_id}/resolve", response_model=AlertOut)
async def resolve_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_db),
):
    alert = await engine_resolve_alert(session, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await session.commit()
    await session.refresh(alert)
    return alert
