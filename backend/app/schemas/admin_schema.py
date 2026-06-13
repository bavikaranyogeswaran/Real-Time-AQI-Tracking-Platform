from datetime import datetime

from pydantic import BaseModel


class CityStatusOut(BaseModel):
    city: str
    country: str
    latest_aqi: int | None
    last_reading_at: datetime | None
    reading_count_7d: int
    data_source: str | None

    model_config = {"from_attributes": True}


class AdminSummaryOut(BaseModel):
    total_readings: int
    readings_by_source: dict[str, int]
    alerts_active: int
    alerts_total_7d: int
    cities_monitored: int
    city_status: list[CityStatusOut]

    model_config = {"from_attributes": True}
