import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Numeric, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AirQualityReading(Base):
    __tablename__ = "air_quality_readings"

    reading_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    location_id: Mapped[str] = mapped_column(String, ForeignKey("locations.location_id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aqi: Mapped[int] = mapped_column(Integer, nullable=False)
    pm25: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    pm10: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    co: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    no2: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    so2: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    o3: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    temperature: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)   # °C
    humidity: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)      # %
    wind_speed: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)    # m/s
    data_source: Mapped[str] = mapped_column(String(100), nullable=False, default="openweather")

    __table_args__ = (
        Index("ix_air_quality_location_timestamp", "location_id", "timestamp"),
        UniqueConstraint("location_id", "timestamp", name="uq_location_timestamp"),
    )
