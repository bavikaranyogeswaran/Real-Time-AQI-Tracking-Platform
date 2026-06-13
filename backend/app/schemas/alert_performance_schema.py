from datetime import date

from pydantic import BaseModel


class AlertByTypeOut(BaseModel):
    alert_type: str
    count: int
    avg_aqi: float

    model_config = {"from_attributes": True}


class AlertByCityOut(BaseModel):
    city: str
    count: int

    model_config = {"from_attributes": True}


class AlertDailyCountOut(BaseModel):
    date: date
    count: int

    model_config = {"from_attributes": True}


class AlertPerformanceOut(BaseModel):
    total: int
    active: int
    resolved: int
    by_type: list[AlertByTypeOut]
    by_city: list[AlertByCityOut]
    daily_counts: list[AlertDailyCountOut]

    model_config = {"from_attributes": True}
