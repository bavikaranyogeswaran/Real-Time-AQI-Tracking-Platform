import uuid
from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    location_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False, default="openweather")
