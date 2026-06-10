import uuid
from sqlalchemy import String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    rule_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    location_id: Mapped[str | None] = mapped_column(String, ForeignKey("locations.location_id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    threshold_value: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
