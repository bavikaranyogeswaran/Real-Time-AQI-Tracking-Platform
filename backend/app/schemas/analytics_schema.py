from datetime import date, datetime
from pydantic import BaseModel


class GapOut(BaseModel):
    gap_start: datetime
    gap_end: datetime
    duration_minutes: int

    model_config = {"from_attributes": True}


class CityComparisonOut(BaseModel):
    city: str
    country: str
    latitude: float
    longitude: float
    latest_aqi: int
    category: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class TrendOut(BaseModel):
    date: date
    avg_aqi: float
    min_aqi: int
    max_aqi: int

    model_config = {"from_attributes": True}
