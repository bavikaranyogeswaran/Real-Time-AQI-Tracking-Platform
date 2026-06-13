from datetime import date, datetime

from pydantic import BaseModel


class ForecastAccuracyRowOut(BaseModel):
    forecast_for: datetime
    predicted_aqi: float
    actual_aqi: int
    error: float

    model_config = {"from_attributes": True}


class ForecastAccuracyOut(BaseModel):
    rows: list[ForecastAccuracyRowOut]
    mae: float
    rmse: float
    sample_count: int

    model_config = {"from_attributes": True}


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


class PollutantTrendOut(BaseModel):
    date: date
    avg_pm25: float | None
    avg_pm10: float | None
    avg_co: float | None
    avg_no2: float | None
    avg_so2: float | None
    avg_o3: float | None

    model_config = {"from_attributes": True}


class DominantPollutantOut(BaseModel):
    pollutant: str
    label: str
    avg_value: float
    safe_limit: float
    exceedance_count: int

    model_config = {"from_attributes": True}
