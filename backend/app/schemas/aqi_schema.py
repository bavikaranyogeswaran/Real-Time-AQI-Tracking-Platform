from datetime import datetime
from pydantic import BaseModel


class PollutantOut(BaseModel):
    pm25: float | None
    pm10: float | None
    co: float | None
    no2: float | None
    so2: float | None
    o3: float | None

    model_config = {"from_attributes": True}


class CurrentAQIOut(BaseModel):
    reading_id: str
    location_id: str
    city: str
    timestamp: datetime
    aqi: int
    category: str
    pm25: float | None
    pm10: float | None
    co: float | None
    no2: float | None
    so2: float | None
    o3: float | None
    data_source: str

    model_config = {"from_attributes": True}


class HistoryAQIOut(BaseModel):
    reading_id: str
    timestamp: datetime
    aqi: int
    category: str
    pm25: float | None
    pm10: float | None
    co: float | None
    no2: float | None
    so2: float | None
    o3: float | None

    model_config = {"from_attributes": True}


class ForecastOut(BaseModel):
    prediction_id: str
    forecast_for: datetime
    predicted_aqi: float
    model_name: str

    model_config = {"from_attributes": True}
