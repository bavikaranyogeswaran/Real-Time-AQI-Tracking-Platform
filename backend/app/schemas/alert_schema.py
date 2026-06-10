from datetime import datetime
from pydantic import BaseModel


class AlertOut(BaseModel):
    alert_id: str
    location_id: str
    alert_type: str
    threshold_value: int
    actual_aqi: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertRuleIn(BaseModel):
    location_id: str | None = None
    alert_type: str
    threshold_value: int
