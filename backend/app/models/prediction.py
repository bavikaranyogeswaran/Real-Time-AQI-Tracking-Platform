import uuid
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AQIPrediction(Base):
    __tablename__ = "aqi_predictions"

    prediction_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    location_id: Mapped[str] = mapped_column(String, ForeignKey("locations.location_id"), nullable=False)
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_aqi: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, default="xgboost")
